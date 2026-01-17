import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from src.config import get_settings
from src.db.factory import make_database
from src.middlewares import (
    AccessControlMiddleware,
    AuditMiddleware,
    AuthMiddleware,
    PerformanceMonitoringMiddleware,
)
from src.routers import agentic_ask, document_management, hybrid_search, ping
from src.routers.admin import audit
from src.routers.auth import login
from src.services.cache.factory import make_cache_client
from src.services.document_sources.factory import make_document_source
from src.services.embeddings.factory import make_embeddings_service
from src.services.langfuse.factory import make_langfuse_tracer
from src.services.ollama.factory import make_ollama_client
from src.services.opensearch.factory import make_opensearch_client
from src.services.security.access_control_service import AccessControlService
from src.services.security.auth_service import AuthService
from src.services.security.audit_logger import AuditLogger
from src.services.telegram.factory import make_telegram_service

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan for the Enterprise Knowledge Base API.
    """
    logger.info("=" * 80)
    logger.info("Starting Enterprise Knowledge Base API")
    logger.info("=" * 80)

    settings = get_settings()
    app.state.settings = settings

    # Initialize database
    database = make_database()
    app.state.database = database
    logger.info("PostgreSQL database connected and initialized")

    # Initialize OpenSearch
    opensearch_client = make_opensearch_client()
    app.state.opensearch_client = opensearch_client

    # Verify OpenSearch connectivity and setup indices
    if opensearch_client.health_check():
        logger.info("OpenSearch connected successfully")
        
        # Setup hybrid index with enterprise schema
        setup_results = opensearch_client.setup_indices(force=False)
        if setup_results.get("hybrid_index"):
            logger.info("Enterprise hybrid index created")
        else:
            logger.info("Enterprise hybrid index already exists")

        # Get index statistics
        try:
            stats = opensearch_client.client.count(index=opensearch_client.index_name)
            logger.info(f"OpenSearch ready: {stats['count']} documents indexed")
        except Exception as e:
            logger.info(f"OpenSearch index ready (stats unavailable: {e})")
    else:
        logger.warning("OpenSearch connection failed - document search features will be limited")

    # Initialize enterprise services
    app.state.embeddings_service = make_embeddings_service()
    app.state.ollama_client = make_ollama_client()
    app.state.langfuse_tracer = make_langfuse_tracer()
    app.state.cache_client = make_cache_client(settings)
    
    # Initialize security services
    app.state.auth_service = AuthService()
    app.state.access_control_service = AccessControlService()
    app.state.audit_logger = AuditLogger(langfuse_tracer=app.state.langfuse_tracer)
    logger.info("Security services initialized: Auth, Access Control, Audit Logging")
    
    # Initialize document source for ingestion
    try:
        app.state.document_source = make_document_source()
        logger.info(f"Document source initialized: {settings.enterprise_source.source_type}")
    except Exception as e:
        logger.warning(f"Document source initialization failed: {e}")
        app.state.document_source = None
    
    logger.info("Core services initialized: OpenSearch, Embeddings, Ollama, Langfuse, Cache, Security")

    # Initialize Telegram bot (optional)
    telegram_service = make_telegram_service(
        opensearch_client=app.state.opensearch_client,
        embeddings_client=app.state.embeddings_service,
        ollama_client=app.state.ollama_client,
        cache_client=app.state.cache_client,
        langfuse_tracer=app.state.langfuse_tracer,
    )

    if telegram_service:
        app.state.telegram_service = telegram_service
        try:
            await telegram_service.start()
            logger.info("Telegram bot started successfully")
        except Exception as e:
            logger.error(f"Failed to start Telegram bot: {e}")
    else:
        logger.info("Telegram bot not configured - skipping initialization")

    logger.info("-" * 80)
    logger.info("Enterprise Knowledge Base API ready for requests")
    logger.info("-" * 80)
    yield

    # Cleanup on shutdown
    logger.info("Shutting down Enterprise Knowledge Base API")
    
    if settings.langfuse.enabled and hasattr(app.state, "langfuse_tracer"):
        app.state.langfuse_tracer.flush()

    if hasattr(app.state, "telegram_service") and app.state.telegram_service:
        await telegram_service.stop()
        logger.info("Telegram bot stopped")

    database.teardown()
    logger.info("Database connections closed")
    logger.info("API shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Enterprise Knowledge Base API",
    description="AI-powered enterprise document search and Q&A with security and compliance",
    version=os.getenv("APP_VERSION", "0.1.0"),
    lifespan=lifespan,
)

# Register middleware
app.add_middleware(AuthMiddleware)
app.add_middleware(AccessControlMiddleware)
app.add_middleware(AuditMiddleware)
app.add_middleware(PerformanceMonitoringMiddleware)
logger.info("Security and performance middleware registered")

# Include API routers
app.include_router(ping.router, prefix="/api/v1")  # Health check endpoint
app.include_router(hybrid_search.router, prefix="/api/v1")  # Search with access control
app.include_router(document_management.router, prefix="/api/v1")  # Document CRUD
app.include_router(login.router, prefix="/api/v1")  # Authentication
app.include_router(audit.router)  # Admin audit endpoints
app.include_router(agentic_ask.router)  # Agentic RAG with security

logger.info("API routers registered and application ready")


if __name__ == "__main__":
    uvicorn.run(
        app,
        port=8000,
        host="0.0.0.0",
        log_level="info",
        access_log=True,
    )
