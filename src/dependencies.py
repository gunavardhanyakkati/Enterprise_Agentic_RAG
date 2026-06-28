from functools import lru_cache
from typing import TYPE_CHECKING, Annotated, Generator, List, Optional

if TYPE_CHECKING:
    from fastapi import Depends, Request
    from sqlalchemy.orm import Session
else:
    try:
        from fastapi import Depends, Header, HTTPException, Request, status
        from sqlalchemy.orm import Session
    except ImportError:
        pass

from src.config import Settings
from src.db.interfaces.base import BaseDatabase
from src.schemas.common.security import User
from src.services.agents.agentic_rag import AgenticRAGService
from src.services.agents.factory import make_agentic_rag_service
from src.services.arxiv.client import ArxivClient
from src.services.cache.client import CacheClient
from src.services.document_sources.factory import make_document_source
from src.services.embeddings.factory import EmbeddingsClient, make_embeddings_service
from src.services.embeddings.jina_client import JinaEmbeddingsClient
from src.services.indexing.hybrid_indexer import HybridIndexingService
from src.services.langfuse.client import LangfuseTracer
from src.services.ollama.client import OllamaClient
from src.services.opensearch.client import OpenSearchClient
from src.services.pdf_parser.parser import PDFParserService
from src.services.security.access_control_service import AccessControlService
from src.services.security.auth_service import AuthService
from src.services.security.audit_logger import AuditLogger
from src.services.telegram.bot import TelegramBot
from src.services.document_lifecycle.version_control_service import VersionControlService

@lru_cache
def get_settings() -> Settings:
    """Get application settings."""
    return Settings()


def get_request_settings(request: Request) -> Settings:
    """Get settings from the request state."""
    return request.app.state.settings


def get_database(request: Request) -> BaseDatabase:
    """Get database from the request state."""
    return request.app.state.database


def get_db_session(database: Annotated[BaseDatabase, Depends(get_database)]) -> Generator[Session, None, None]:
    """Get database session dependency."""
    with database.get_session() as session:
        yield session


def get_opensearch_client(request: Request) -> OpenSearchClient:
    """Get OpenSearch client from the request state."""
    return request.app.state.opensearch_client


def get_arxiv_client(request: Request) -> ArxivClient:
    """Get arXiv client from the request state."""
    return request.app.state.arxiv_client


def get_pdf_parser(request: Request) -> PDFParserService:
    """Get PDF parser service from the request state."""
    return request.app.state.pdf_parser


def get_embeddings_service(request: Request) -> EmbeddingsClient:
    """Get embeddings service from the request state."""
    return request.app.state.embeddings_service


def get_ollama_client(request: Request) -> OllamaClient:
    """Get Ollama client from the request state."""
    return request.app.state.ollama_client


def get_langfuse_tracer(request: Request) -> LangfuseTracer:
    """Get Langfuse tracer from the request state."""
    return request.app.state.langfuse_tracer


def get_cache_client(request: Request) -> CacheClient | None:
    """Get cache client from the request state."""
    return getattr(request.app.state, "cache_client", None)


def get_telegram_service(request: Request) -> Optional[TelegramBot]:
    """Get Telegram service from the request state."""
    return getattr(request.app.state, "telegram_service", None)


def get_document_source(request: Request):
    """Get document source from the request state."""
    return getattr(request.app.state, "document_source", None)


def get_auth_service(request: Request) -> AuthService:
    """Get authentication service from the request state."""
    return request.app.state.auth_service


def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None),
) -> User:
    """Get current authenticated user from JWT token.
    
    Args:
        request: The incoming request
        authorization: Authorization header with Bearer token
        
    Returns:
        Authenticated User object
        
    Raises:
        HTTPException: If token is missing or invalid
    """
    auth_service = get_auth_service(request)
    
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract token from "Bearer <token>" format
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = authorization.replace("Bearer ", "")
    return auth_service.get_current_user(token)


def get_access_control_service(request: Request) -> AccessControlService:
    """Get access control service from the request state."""
    return request.app.state.access_control_service


def get_audit_logger(request: Request) -> AuditLogger:
    """Get audit logger from the request state."""
    return request.app.state.audit_logger


def get_agentic_rag_service(
    opensearch: Annotated[OpenSearchClient, Depends(get_opensearch_client)],
    ollama: Annotated[OllamaClient, Depends(get_ollama_client)],
    embeddings: Annotated[EmbeddingsClient, Depends(get_embeddings_service)],
    langfuse: Annotated[LangfuseTracer, Depends(get_langfuse_tracer)],
    user: Annotated[User, Depends(get_current_user)],  # NEW: User context
    settings: Annotated[Settings, Depends(get_settings)],
) -> AgenticRAGService:
    """Get agentic RAG service with user context."""
    return make_agentic_rag_service(
        opensearch_client=opensearch,
        ollama_client=ollama,
        embeddings_client=embeddings,
        langfuse_tracer=langfuse,
        model=settings.ollama_model,
    )


def get_version_control_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> VersionControlService:
    """Get version control service."""
    return VersionControlService(db_session=session)


def get_retention_service(
    session: Annotated[Session, Depends(get_db_session)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
) -> "RetentionService":
    """Get retention service."""
    from src.repositories.document import DocumentRepository
    from src.services.document_lifecycle.retention_service import RetentionService
    
    repository = DocumentRepository(session)
    return RetentionService(repository=repository, audit_logger=audit_logger)


SettingsDep = Annotated[Settings, Depends(get_request_settings)]
AgenticRAGDep = Annotated[AgenticRAGService, Depends(get_agentic_rag_service)]
DatabaseDep = Annotated[BaseDatabase, Depends(get_database)]
SessionDep = Annotated[Session, Depends(get_db_session)]
OpenSearchDep = Annotated[OpenSearchClient, Depends(get_opensearch_client)]
ArxivDep = Annotated[ArxivClient, Depends(get_arxiv_client)]
PDFParserDep = Annotated[PDFParserService, Depends(get_pdf_parser)]
EmbeddingsDep = Annotated[EmbeddingsClient, Depends(get_embeddings_service)]
OllamaDep = Annotated[OllamaClient, Depends(get_ollama_client)]
LangfuseDep = Annotated[LangfuseTracer, Depends(get_langfuse_tracer)]
CacheDep = Annotated[CacheClient | None, Depends(get_cache_client)]
TelegramDep = Annotated[Optional[TelegramBot], Depends(get_telegram_service)]
UserDep = Annotated[User, Depends(get_current_user)]  # NEW: User dependency
AuthDep = Annotated[AuthService, Depends(get_auth_service)]
AccessControlDep = Annotated[AccessControlService, Depends(get_access_control_service)]
AuditLoggerDep = Annotated[AuditLogger, Depends(get_audit_logger)]
VersionControlDep = Annotated[VersionControlService, Depends(get_version_control_service)]
