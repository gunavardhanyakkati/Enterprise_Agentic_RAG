import logging
import time
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from src.schemas.common.security import User
from src.services.security.access_control_service import AccessControlService
from src.services.security.audit_logger import AuditLogger

logger = logging.getLogger(__name__)


# Legacy simple logging functions for backward compatibility
def log_request(method: str, path: str) -> None:
    """Simple request logging for Week 1."""
    logger.info(f"{method} {path}")


def log_error(error: str, method: str, path: str) -> None:
    """Simple error logging for Week 1."""
    logger.error(f"Error in {method} {path}: {error}")


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware for JWT authentication and user context injection."""

    async def dispatch(self, request: Request, call_next):
        """Process request and inject user context from JWT token."""
        # Skip auth for health check and public endpoints
        if request.url.path in ("/health", "/api/v1/health", "/docs", "/openapi.json"):
            return await call_next(request)

        auth_service = request.app.state.auth_service
        auth_header = request.headers.get("Authorization", "")

        if auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            try:
                user = auth_service.get_current_user(token)
                request.state.user = user
                logger.debug(f"Authenticated user: {user.username}")
            except Exception as e:
                logger.warning(f"Authentication failed: {e}")
                request.state.user = None
        else:
            request.state.user = None

        response = await call_next(request)
        return response


class AccessControlMiddleware(BaseHTTPMiddleware):
    """Middleware for document access control checks."""

    async def dispatch(self, request: Request, call_next):
        """Check user access permissions for document-related endpoints."""
        # Skip for non-document endpoints and public routes
        if not any(path in request.url.path for path in ("/document", "/search", "/ask")):
            return await call_next(request)

        access_control: AccessControlService = request.app.state.access_control_service
        user: Optional[User] = getattr(request.state, "user", None)

        # Allow access if auth is disabled or user is None (public endpoints)
        if not access_control.settings.rbac_enabled or user is None:
            return await call_next(request)

        # For search endpoints, we'll filter results at the service layer
        # For specific document endpoints, check access here
        if "document" in request.url.path and request.method in ("GET", "PUT", "DELETE"):
            # Extract document ID from path or query
            document_id = self._extract_document_id(request)
            if document_id:
                # This is simplified - in production you'd fetch the document and check access
                logger.debug(f"Would check access for document {document_id} by user {user.username}")

        response = await call_next(request)
        return response

    def _extract_document_id(self, request: Request) -> Optional[str]:
        """Extract document ID from request path or query parameters."""
        # Path pattern: /api/v1/documents/{document_id}
        path_parts = request.url.path.split("/")
        for i, part in enumerate(path_parts):
            if part == "documents" and i + 1 < len(path_parts):
                return path_parts[i + 1]
        
        # Check query params
        return request.query_params.get("document_id")


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware for logging all document access and system events."""

    async def dispatch(self, request: Request, call_next):
        """Log request and response for audit trail."""
        # Skip for non-relevant endpoints
        if not any(path in request.url.path for path in ("/document", "/search", "/ask", "/upload")):
            return await call_next(request)

        audit_logger: AuditLogger = request.app.state.audit_logger
        user: Optional[User] = getattr(request.state, "user", None)
        
        # Capture request start time for latency tracking
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate latency
        latency = time.time() - start_time
        
        # Log audit event if enabled
        if audit_logger.enabled:
            await self._log_audit_event(request, response, user, latency)
        
        return response

    async def _log_audit_event(self, request: Request, response, user: Optional[User], latency: float):
        """Create and log audit event."""
        audit_logger: AuditLogger = request.app.state.audit_logger
        
        # Extract relevant info
        user_id = user.id if user else "anonymous"
        endpoint = request.url.path
        method = request.method
        status_code = response.status_code
        
        # Only log successful accesses (2xx) and security-relevant failures (401, 403, 404)
        if status_code < 400 or status_code in (401, 403, 404):
            event_details = {
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
                "latency_ms": round(latency * 1000, 2),
                "ip_address": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            }
            
            if "document" in endpoint:
                document_id = self._extract_document_id(request)
                if document_id:
                    audit_logger.log_document_access(user_id, document_id, "api_access", event_details)
            else:
                audit_logger.log_audit_event("api_request", user_id, endpoint, event_details)

    def _extract_document_id(self, request: Request) -> Optional[str]:
        """Extract document ID from request."""
        path_parts = request.url.path.split("/")
        for i, part in enumerate(path_parts):
            if part == "documents" and i + 1 < len(path_parts):
                return path_parts[i + 1]
        return request.query_params.get("document_id")


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for API performance monitoring and metrics."""

    async def dispatch(self, request: Request, call_next):
        """Track request timing and performance metrics."""
        # Skip for non-API endpoints
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        start_time = time.time()
        response = await call_next(request)
        end_time = time.time()

        # Log slow requests (>1 second)
        latency = end_time - start_time
        if latency > 1.0:
            logger.warning(
                f"Slow API request: {request.method} {request.url.path} "
                f"took {latency:.2f}s (status: {response.status_code})"
            )

        # Add response header with request ID for tracing
        response.headers["X-Request-ID"] = getattr(request.state, "request_id", "unknown")
        response.headers["X-Response-Time"] = f"{latency:.3f}s"

        return response
