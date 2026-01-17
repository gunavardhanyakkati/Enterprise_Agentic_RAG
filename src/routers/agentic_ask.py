import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from src.dependencies import (
    AccessControlDep,
    AgenticRAGDep,
    AuditLoggerDep,
    CacheDep,
    EmbeddingsDep,
    LangfuseDep,
    OpenSearchDep,
    UserDep,
)
from src.schemas.api.ask import AgenticAskResponse, AskRequest, FeedbackRequest, FeedbackResponse
from src.schemas.common.security import User
from src.services.security.access_control_service import AccessControlService
from src.services.security.audit_logger import AuditLogger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["agentic-rag"])


@router.post("/ask-agentic", response_model=AgenticAskResponse)
async def ask_agentic(
    request: AskRequest,
    agentic_rag: AgenticRAGDep,
    user: User = UserDep,
    access_control: AccessControlService = AccessControlDep,
    audit_logger: AuditLogger = AuditLoggerDep,
    cache_client: CacheDep = None,
) -> AgenticAskResponse:
    """
    Agentic RAG endpoint with intelligent retrieval, query refinement, and enterprise access control.
    
    The agent will:
    1. Validate query scope and user permissions
    2. Determine if document retrieval is needed
    3. Filter retrieved documents by user access levels
    4. Grade documents for relevance
    5. Rewrite query if needed
    6. Generate answer with citations and reasoning
    
    All actions are logged for audit compliance.
    
    Args:
        request: Question and search parameters
        agentic_rag: Injected agentic RAG service
        user: Authenticated user
        access_control: Access control service for permission checks
        audit_logger: Audit logger for compliance tracking
        cache_client: Optional cache client for response caching
        
    Returns:
        Answer with sources, reasoning steps, and trace ID
        
    Raises:
        HTTPException: If processing fails or access denied
    """
    try:
        logger.info(f"Agentic RAG query by user {user.username}: '{request.query[:100]}...'")
        
        # Log query initiation for audit
        audit_logger.log_document_access(user, "agentic_rag", "query", {
            "query": request.query,
            "model": request.model,
            "use_hybrid": request.use_hybrid,
        })
        
        # Check if user has permission to perform searches at requested access level
        if not access_control.can_access_level(user, "internal"):  # Default minimum for search
            audit_logger.log_security_event(
                user=user,
                event="search_access_denied",
                reason=f"User {user.username} attempted agentic search without permission",
                severity="medium",
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to search documents",
            )
        
        # Check cache if available
        if cache_client:
            try:
                cached_response = await cache_client.find_cached_response(request, user.access_levels)
                if cached_response:
                    logger.info(f"Cache hit for user {user.username}")
                    # Log cached response access
                    audit_logger.log_document_access(user, "agentic_rag", "cached_response", {
                        "query": request.query,
                        "sources_count": len(cached_response.sources),
                    })
                    return AgenticAskResponse(
                        query=cached_response.query,
                        answer=cached_response.answer,
                        sources=cached_response.sources,
                        chunks_used=cached_response.chunks_used,
                        search_mode=cached_response.search_mode,
                        reasoning_steps=["Retrieved from cache"],
                        retrieval_attempts=0,
                        trace_id="cache_hit",
                    )
            except Exception as e:
                logger.warning(f"Cache check failed: {e}")
        
        # Execute agentic RAG with user context
        result = await agentic_rag.ask(
            query=request.query,
            user_id=user.id,  # Pass user ID for trace correlation
        )
        
        # Log successful answer generation
        audit_logger.log_document_access(user, "agentic_rag", "answer_generated", {
            "query": request.query,
            "sources_count": len(result.get("sources", [])),
            "retrieval_attempts": result.get("retrieval_attempts", 0),
            "execution_time": result.get("execution_time", 0),
        })
        
        # Filter sources to only those user can access (additional safety layer)
        # Note: This should ideally be done at retrieval time, but double-checking here
        filtered_sources = []
        for source in result.get("sources", []):
            # Extract document ID from source URL
            doc_id = source.split("/")[-1].replace(".pdf", "") if "arxiv.org" in source else None
            # In enterprise context, sources would be internal document references
            # For now, we pass through but this is where you'd filter by access control
            
            # TODO: Implement proper source filtering based on document access levels
            filtered_sources.append(source)
        
        logger.info(
            f"Agentic RAG completed for user {user.username}: "
            f"answer length={len(result['answer'])} chars, "
            f"sources={len(filtered_sources)}, "
            f"attempts={result.get('retrieval_attempts', 0)}"
        )
        
        return AgenticAskResponse(
            query=result["query"],
            answer=result["answer"],
            sources=filtered_sources,
            chunks_used=request.top_k,
            search_mode="hybrid" if request.use_hybrid else "bm25",
            reasoning_steps=result.get("reasoning_steps", []),
            retrieval_attempts=result.get("retrieval_attempts", 0),
            trace_id=result.get("trace_id"),
        )

    except ValueError as e:
        logger.error(f"Validation error in agentic RAG: {e}")
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in agentic RAG processing: {e}", exc_info=True)
        
        # Log failed request
        audit_logger.log_security_event(
            user=user,
            event="agentic_rag_failure",
            reason=f"Processing failed: {str(e)}",
            severity="low",
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing question: {str(e)}",
        )


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    langfuse_tracer: LangfuseDep,
    user: User = UserDep,
    audit_logger: AuditLogger = AuditLoggerDep,
) -> FeedbackResponse:
    """
    Submit user feedback for an agentic RAG response with audit logging.
    
    This endpoint allows users to rate answer quality and provide comments.
    Feedback is tracked in Langfuse for model improvement and in audit logs
    for compliance.
    
    Args:
        request: Feedback data including trace_id, score, and optional comment
        langfuse_tracer: Injected Langfuse tracer for trace correlation
        user: Authenticated user providing feedback
        audit_logger: Audit logger for feedback tracking
        
    Returns:
        FeedbackResponse indicating success or failure
        
    Raises:
        HTTPException: If feedback submission fails
    """
    try:
        if not langfuse_tracer:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Langfuse tracing is disabled. Cannot submit feedback.",
            )

        logger.info(f"Feedback submitted by user {user.username} for trace {request.trace_id}: score={request.score}")

        success = langfuse_tracer.submit_feedback(
            trace_id=request.trace_id,
            score=request.score,
            comment=request.comment,
        )

        if success:
            # Log feedback submission for audit
            audit_logger.log_document_access(user, "feedback", "submit", {
                "trace_id": request.trace_id,
                "score": request.score,
                "has_comment": bool(request.comment),
            })
            
            # Flush to ensure feedback is sent immediately
            langfuse_tracer.flush()

            return FeedbackResponse(
                success=True,
                message="Feedback recorded successfully. Thank you for your input!",
            )
        else:
            logger.error(f"Failed to submit feedback to Langfuse")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to submit feedback to Langfuse",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}", exc_info=True)
        
        # Log feedback submission failure
        audit_logger.log_security_event(
            user=user,
            event="feedback_submission_failure",
            reason=str(e),
            severity="low",
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error submitting feedback: {str(e)}",
        )
