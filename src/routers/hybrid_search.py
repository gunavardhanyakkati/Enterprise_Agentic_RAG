import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status

from src.dependencies import (
    AccessControlDep,
    AuditLoggerDep,
    EmbeddingsDep,
    OpenSearchDep,
    UserDep,
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
    user: User = UserDep,
    access_control: AccessControlService = AccessControlDep,
    audit_logger: AuditLogger = AuditLoggerDep,
) -> SearchResponse:
    """
    Hybrid search endpoint supporting multiple search modes with enterprise access control.
    
    This endpoint performs hybrid search (BM25 + vector) on documents while enforcing
    access control based on user permissions. All search queries are logged for audit compliance.
    
    Args:
        request: Search request with query and filters
        opensearch_client: OpenSearch client for search
        embeddings_service: Embeddings service for vector search
        user: Authenticated user making the request
        access_control: Access control service for permission checks
        audit_logger: Audit logger for compliance tracking
        
    Returns:
        Search response with filtered results
        
    Raises:
        HTTPException: If search service unavailable or access denied
    """
    try:
        # Log the search query for audit
        audit_logger.log_document_access(user, "search", "query", {
            "query": request.query,
            "use_hybrid": request.use_hybrid,
            "size": request.size,
            "filters": {
                "department": request.categories,  # Reusing categories field for department filter
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
        
        # Filter by department if specified
        if request.categories:  # Reusing categories field for department filter
            additional_filters.append({"terms": {"department": request.categories}})
            
        # Filter by access level - users can only see documents at or below their max level
        max_user_level = max(
            access_control.ACCESS_LEVEL_HIERARCHY.get(level, -1) 
            for level in user_access_levels
        )
        
        # Add access level filter to ensure user can only see permitted documents
        accessible_levels = [
            level for level, value in access_control.ACCESS_LEVEL_HIERARCHY.items()
            if value <= max_user_level
        ]
        additional_filters.append({"terms": {"access_level": accessible_levels}})
        
        logger.debug(f"Access level filter applied: {accessible_levels}")

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

        # Extract and filter hits to double-check access control
        hits = []
        for hit in results.get("hits", []):
            # Verify user can access this specific document's access level
            doc_access_level = hit.get("access_level", "internal")
            
            if access_control.can_access_level(user, doc_access_level):
                hits.append(
                    SearchHit(
                        arxiv_id=hit.get("document_id", ""),  # Using document_id instead of arxiv_id
                        title=hit.get("title", ""),
                        authors=hit.get("contributors", []),  # Using contributors instead of authors
                        abstract=hit.get("description", ""),  # Using description instead of abstract
                        published_date=hit.get("created_at"),  # Using created_at instead of published_date
                        pdf_url=hit.get("file_path", ""),  # Using file_path instead of pdf_url
                        score=hit.get("score", 0.0),
                        highlights=hit.get("highlights"),
                        chunk_text=hit.get("chunk_text"),
                        chunk_id=hit.get("chunk_id"),
                        section_name=hit.get("section_name"),
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
