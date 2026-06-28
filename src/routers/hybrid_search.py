import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status

from src.dependencies import (
    AccessControlDep,
    AuditLoggerDep,
    EmbeddingsDep,
    OpenSearchDep,
    UserDep,
    SessionDep,
)
from src.schemas.api.search import HybridSearchRequest, SearchHit, SearchResponse
from src.schemas.common.security import User
from src.services.security.access_control_service import AccessControlService
from src.services.security.audit_logger import AuditLogger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hybrid-search", tags=["hybrid-search"])


@router.post("/", response_model=SearchResponse)
async def hybrid_search(
    request: HybridSearchRequest,
    opensearch_client: OpenSearchDep,
    embeddings_service: EmbeddingsDep,
    user: UserDep,
    access_control: AccessControlDep,
    audit_logger: AuditLoggerDep,
    session: SessionDep,
) -> SearchResponse:
    """
    Hybrid search endpoint supporting multiple search modes with enterprise access control.
    """
    try:
        # Log the search query for audit
        audit_logger.log_document_access(user, "search", "query", {
            "query": request.query,
            "use_hybrid": request.use_hybrid,
            "size": request.size,
            "filters": {
                "document_type": request.document_type,
                "department": request.department,
                "access_level": request.access_level,
            },
        })
        
        if not opensearch_client.health_check():
            raise HTTPException(status_code=503, detail="Search service is currently unavailable")

        # Determine which access levels the user can search
        user_access_levels = access_control.get_user_access_levels(user)
        logger.info(f"Search by user {user.username} with access levels: {user_access_levels}")

        # Generate query embedding for hybrid search if needed
        query_embedding = None
        if request.use_hybrid:
            try:
                query_embedding = await embeddings_service.embed_query(request.query)
                logger.info("Generated query embedding for hybrid search")
            except Exception as e:
                logger.warning(f"Failed to generate embeddings, falling back to BM25: {e}")
                query_embedding = None

        logger.info(f"Hybrid search: '{request.query}' (hybrid: {request.use_hybrid and query_embedding is not None})")

        # Build additional filters for enterprise metadata
        additional_filters = []
        
        # Filter by legacy categories field if specified
        if request.categories:
            additional_filters.append({"terms": {"department": request.categories}})
            
        # Filter by access level - users can only see documents at or below their max level
        max_user_level = max(
            access_control.ACCESS_LEVEL_HIERARCHY.get(level, -1) 
            for level in user_access_levels
        )
        
        accessible_levels = [
            level for level, value in access_control.ACCESS_LEVEL_HIERARCHY.items()
            if value <= max_user_level
        ]
        additional_filters.append({"terms": {"access_level": accessible_levels}})
        
        logger.debug(f"Access level filter applied: {accessible_levels}")

        # Relational SQL Filtering logic via Postgres matching document IDs
        from sqlalchemy import select
        from src.models.document import Document
        
        # Build query
        stmt = select(Document.document_id)
        has_sql_filters = False
        
        if request.document_type:
            stmt = stmt.where(Document.document_type == request.document_type)
            has_sql_filters = True
        if request.department:
            stmt = stmt.where(Document.department == request.department)
            has_sql_filters = True
        if request.access_level:
            stmt = stmt.where(Document.access_level == request.access_level)
            has_sql_filters = True
            
        matching_doc_ids = []
        if has_sql_filters:
            result = session.scalars(stmt)
            matching_doc_ids = list(result)
            if not matching_doc_ids:
                return SearchResponse(
                    query=request.query,
                    total=0,
                    hits=[],
                    size=request.size,
                    **{"from": request.from_},
                    search_mode="hybrid" if (request.use_hybrid and query_embedding) else "bm25",
                )
                
        # Handle Notice Period and Liability Cap filters inside metadata
        if request.notice_period_days or request.min_liability_cap:
            filtered_ids = []
            stmt_all = select(Document)
            if matching_doc_ids:
                stmt_all = stmt_all.where(Document.document_id.in_(matching_doc_ids))
            docs = session.scalars(stmt_all).all()
            
            for doc in docs:
                meta = doc.extracted_metadata or {}
                
                # Check Notice Period
                if request.notice_period_days:
                    notice_val = meta.get("termination_notice_period", {})
                    val_str = notice_val.get("value", "") if isinstance(notice_val, dict) else str(notice_val)
                    import re
                    digits = [int(s) for s in re.findall(r'\d+', val_str)]
                    if digits:
                        doc_days = digits[0]
                        if doc_days != request.notice_period_days:
                            continue
                    else:
                        continue
                        
                # Check Liability Cap
                if request.min_liability_cap:
                    liab_val = meta.get("liability_cap", {})
                    val_str = liab_val.get("value", "") if isinstance(liab_val, dict) else str(liab_val)
                    import re
                    digits = [int(s) for s in re.findall(r'\d+', val_str.replace(",", ""))]
                    if digits:
                        doc_cap = digits[0]
                        if doc_cap < request.min_liability_cap:
                            continue
                    else:
                        continue
                        
                filtered_ids.append(doc.document_id)
            matching_doc_ids = filtered_ids
            has_sql_filters = True
            
            if not matching_doc_ids:
                return SearchResponse(
                    query=request.query,
                    total=0,
                    hits=[],
                    size=request.size,
                    **{"from": request.from_},
                    search_mode="hybrid" if (request.use_hybrid and query_embedding) else "bm25",
                )
                
        if has_sql_filters:
            additional_filters.append({"terms": {"document_id": matching_doc_ids}})

        # Perform search with enterprise filters
        results = opensearch_client.search_unified(
            query=request.query,
            query_embedding=query_embedding,
            size=request.size,
            from_=request.from_,
            categories=request.categories,
            latest=request.latest_papers,
            use_hybrid=request.use_hybrid and query_embedding is not None,
            min_score=request.min_score,
            additional_filters=additional_filters if additional_filters else None,
        )

        # Batch-fetch document metadata and compliance reports from the PostgreSQL database
        doc_ids = list({hit.get("document_id") for hit in results.get("hits", []) if hit.get("document_id")})
        db_docs = {}
        if doc_ids:
            from sqlalchemy import select
            from src.models.document import Document
            stmt_db = select(Document).where(Document.document_id.in_(doc_ids))
            db_docs = {d.document_id: d for d in session.scalars(stmt_db).all()}

        # Extract and filter hits to double-check access control
        hits = []
        for hit in results.get("hits", []):
            # Verify user can access this specific document's access level
            doc_access_level = hit.get("access_level", "internal")
            
            if access_control.can_access_level(user, doc_access_level):
                doc_id = hit.get("document_id", "")
                db_doc = db_docs.get(doc_id)
                
                # Fetch compliance report if available in DB
                compliance_report_dict = None
                if db_doc and db_doc.compliance_report:
                    compliance_report_dict = db_doc.compliance_report
                
                hits.append(
                    SearchHit(
                        arxiv_id=doc_id,  # Using document_id instead of arxiv_id
                        external_id=doc_id,
                        title=hit.get("title", ""),
                        contributors=hit.get("contributors", []),
                        authors=hit.get("contributors", []),
                        abstract=hit.get("description", ""),
                        source_created_at=hit.get("created_at"),
                        created_at=hit.get("created_at"),
                        source_url=hit.get("file_path", ""),
                        pdf_url=hit.get("file_path", ""),
                        score=hit.get("score", 0.0),
                        highlights=hit.get("highlights"),
                        chunk_text=hit.get("chunk_text"),
                        chunk_id=hit.get("chunk_id"),
                        section_name=hit.get("section_name"),
                        document_type=hit.get("document_type") or (db_doc.document_type if db_doc else None),
                        access_level=doc_access_level,
                        compliance_report=compliance_report_dict,
                    )
                )
            else:
                logger.warning(
                    f"Access control mismatch: User {user.username} can access level {doc_access_level} "
                    f"but document {hit.get('document_id')} was not filtered by OpenSearch"
                )

        # Log search results for audit
        audit_logger.log_document_access(user, "search", "results", {
            "query": request.query,
            "results_count": len(hits),
            "total_found": results.get("total", 0),
        })
        
        logger.info(
            f"Search completed: {len(hits)} results returned (user could access {len(hits)} "
            f"out of {results.get('total', 0)} total matches)"
        )

        search_response = SearchResponse(
            query=request.query,
            total=len(hits),
            hits=hits,
            size=request.size,
            **{"from": request.from_},
            search_mode="hybrid" if (request.use_hybrid and query_embedding) else "bm25",
        )

        return search_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Hybrid search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
