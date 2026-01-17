import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from src.config import get_settings
from src.schemas.common.security import User

logger = logging.getLogger(__name__)


class AuditLogger:
    """Compliance audit logger for document access and system events."""

    def __init__(self, langfuse_tracer=None):
        """Initialize audit logger.
        
        Args:
            langfuse_tracer: Optional Langfuse tracer for trace correlation
        """
        self.settings = get_settings()
        self.langfuse_tracer = langfuse_tracer
        self.enabled = self.settings.security.rbac_enabled
        logger.info(f"Audit logger initialized (enabled: {self.enabled})")

    def _log_event(self, event_type: str, user: User, resource: str, details: Dict[str, Any]):
        """Internal method to log audit events.
        
        Args:
            event_type: Type of audit event
            user: The user performing the action
            resource: Resource identifier (e.g., 'document:abc123')
            details: Additional event details
        """
        if not self.enabled:
            return

        try:
            audit_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": event_type,
                "user_id": user.id if user else "system",
                "username": user.username if user else "system",
                "resource": resource,
                "details": details,
            }

            # Log as structured JSON for SIEM integration
            logger.info(f"AUDIT: {json.dumps(audit_record)}")

            # Also send to Langfuse if available
            if self.langfuse_tracer and self.langfuse_tracer.client:
                try:
                    trace_id = self.langfuse_tracer.get_trace_id()
                    self.langfuse_tracer.client.event(
                        name=event_type,
                        user_id=user.id if user else "system",
                        metadata=audit_record,
                    )
                except Exception as e:
                    logger.warning(f"Failed to send audit event to Langfuse: {e}")

        except Exception as e:
            # Never let audit logging break the main application
            logger.error(f"Failed to log audit event: {e}", exc_info=True)

    def log_document_access(self, user: User, document_id: str, action: str = "read"):
        """Log when a user accesses a document.
        
        Args:
            user: The authenticated user
            document_id: ID of the accessed document
            action: Type of access (read, search, download)
        """
        self._log_event(
            event_type="document_access",
            user=user,
            resource=f"document:{document_id}",
            details={
                "action": action,
                "access_level": user.access_levels,
            },
        )
        logger.debug(f"Logged document access: user={user.username}, doc={document_id}, action={action}")

    def log_document_modification(self, user: User, document_id: str, action: str, changes: Optional[Dict[str, Any]] = None):
        """Log document creation, update, or deletion.
        
        Args:
            user: The authenticated user
            document_id: ID of the modified document
            action: create, update, delete, version
            changes: Dictionary of changes made
        """
        self._log_event(
            event_type="document_modification",
            user=user,
            resource=f"document:{document_id}",
            details={
                "action": action,
                "changes": changes or {},
            },
        )
        logger.info(f"Logged document modification: user={user.username}, doc={document_id}, action={action}")

    def log_security_event(self, user: Optional[User], event: str, reason: str, severity: str = "medium"):
        """Log security-related events like failed auth or access denied.
        
        Args:
            user: The user involved (None for system events)
            event: Security event type (auth_failure, access_denied, etc.)
            reason: Explanation of the event
            severity: low, medium, high, critical
        """
        self._log_event(
            event_type="security_event",
            user=user,
            resource="security",
            details={
                "event": event,
                "reason": reason,
                "severity": severity,
            },
        )
        logger.warning(f"Security event logged: {event}, severity={severity}, reason={reason}")

    def log_retention_action(self, document_id: str, action: str, reason: str):
        """Log retention policy enforcement actions.
        
        Args:
            document_id: ID of the affected document
            action: archive, delete, notify
            reason: Policy violation or expiration
        """
        self._log_event(
            event_type="retention_policy",
            user=None,  # System action
            resource=f"document:{document_id}",
            details={
                "action": action,
                "reason": reason,
                "retention_days": self.settings.document_lifecycle.retention_days,
            },
        )
        logger.info(f"Logged retention action: doc={document_id}, action={action}")

    async def get_audit_logs(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> list:
        """Retrieve audit logs for admin review.
        
        Args:
            user_id: Filter logs by user
            event_type: Filter logs by event type
            start_date: Filter logs from this date
            end_date: Filter logs to this date
            limit: Maximum number of logs to return
            
        Returns:
            List of audit log entries
        """
        # TODO: Implement actual audit log retrieval from database
        # For now, this is a placeholder that would query an audit_logs table
        logger.warning("Audit log retrieval not yet implemented - returning empty list")
        return []

    def log_user_login(self, user: User, success: bool, ip_address: Optional[str] = None):
        """Log user login attempts.
        
        Args:
            user: The user attempting to login
            success: Whether login was successful
            ip_address: Client IP address
        """
        event = "login_success" if success else "login_failure"
        self._log_event(
            event_type=event,
            user=user,
            resource="authentication",
            details={
                "ip_address": ip_address,
                "user_agent": "",  # Could be extracted from request headers
            },
        )
        logger.info(f"Login attempt logged for user={user.username}, success={success}")

    def log_permission_check(self, user: User, resource: str, action: str, granted: bool):
        """Log permission check outcomes.
        
        Args:
            user: The user requesting access
            resource: Resource being accessed
            action: Action being performed
            granted: Whether permission was granted
        """
        if not granted:
            self.log_security_event(
                user=user,
                event="access_denied",
                reason=f"User lacks {action} permission on {resource}",
                severity="medium",
            )
