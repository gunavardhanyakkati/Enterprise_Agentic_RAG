import logging
from typing import List

from src.config import get_settings
from src.models.document import Document
from src.schemas.common.security import User

logger = logging.getLogger(__name__)


class AccessControlService:
    """Role-based access control service for document permissions."""

    ACCESS_LEVEL_HIERARCHY = {
        "public": 0,
        "internal": 1,
        "confidential": 2,
        "restricted": 3,
    }

    def __init__(self):
        self.settings = get_settings()
        self.security_settings = self.settings.security

    def get_user_access_levels(self, user: User) -> List[str]:
        """Get list of access levels a user can view.
        
        Args:
            user: The authenticated user
            
        Returns:
            List of accessible access level strings
        """
        # If RBAC is disabled, user can access all levels
        if not self.security_settings.rbac_enabled:
            return list(self.ACCESS_LEVEL_HIERARCHY.keys())
        
        # Admin roles have unrestricted access
        if any(role in self.security_settings.admin_roles for role in user.roles):
            logger.debug(f"Admin user {user.username} has unrestricted access")
            return list(self.ACCESS_LEVEL_HIERARCHY.keys())
        
        # Return user's explicit access levels
        return user.access_levels

    def can_access_level(self, user: User, required_level: str) -> bool:
        """Check if user can access documents at the given access level.
        
        Args:
            user: The authenticated user
            required_level: The required access level
            
        Returns:
            True if user can access, False otherwise
        """
        if not self.security_settings.rbac_enabled:
            return True
        
        user_levels = self.get_user_access_levels(user)
        
        # If user doesn't have this explicit level, check hierarchy
        if required_level not in user_levels:
            logger.debug(f"User {user.username} does not have explicit access to {required_level}")
            return False
        
        # Check hierarchy level (user must have at least this level)
        user_max_level = max(
            self.ACCESS_LEVEL_HIERARCHY.get(level, -1) for level in user_levels
        )
        required_level_value = self.ACCESS_LEVEL_HIERARCHY.get(required_level, 999)
        
        can_access = user_max_level >= required_level_value
        logger.debug(
            f"User {user.username} access check: {can_access} "
            f"(user_levels={user_levels}, required={required_level})"
        )
        return can_access

    def can_access_document(self, user: User, document: Document) -> bool:
        """Check if user can access a specific document.
        
        Args:
            user: The authenticated user
            document: The document to check
            
        Returns:
            True if user can access the document, False otherwise
        """
        # Check access level first
        if not self.can_access_level(user, document.access_level):
            logger.info(
                f"Access denied for user {user.username} to document {document.document_id} "
                f"(required_level={document.access_level}, user_levels={user.access_levels})"
            )
            return False
        
        # Department check (optional - users can access documents from any department
        # if they have the appropriate access level)
        logger.debug(
            f"Access granted for user {user.username} to document {document.document_id}"
        )
        return True

    def has_permission(self, user: User, resource: str, action: str, access_level: str) -> bool:
        """Check if user has specific permission for an action.
        
        Args:
            user: The authenticated user
            resource: Resource name (e.g., 'document', 'audit_log')
            action: Action to perform (e.g., 'read', 'write', 'delete')
            access_level: Access level of the resource
            
        Returns:
            True if user has permission, False otherwise
        """
        if not self.security_settings.rbac_enabled:
            return True
        
        # Admin roles bypass all permission checks
        if any(role in self.security_settings.admin_roles for role in user.roles):
            logger.debug(f"Admin user {user.username} bypassed permission check")
            return True
        
        # Basic permission model
        if action == "read":
            return self.can_access_level(user, access_level)
        elif action in ["write", "update", "create"]:
            # Users can only modify documents at access levels they can read
            # AND they must be the owner or have editor role
            return self.can_access_level(user, access_level) and (
                user.id == self._get_owner_id(resource) or "editor" in user.roles
            )
        elif action == "delete":
            # Only admins or owners can delete
            return any(role in self.security_settings.admin_roles for role in user.roles) or "owner" in user.roles
        
        logger.warning(f"Unknown permission check: {resource}.{action} for level {access_level}")
        return False

    def _get_owner_id(self, resource: str) -> str:
        """Extract owner ID from resource string.
        
        Args:
            resource: Resource identifier (e.g., 'document:abc123')
            
        Returns:
            Owner ID if extractable, empty string otherwise
        """
        # This is a simplified implementation
        # In a real system, you'd query the database for the resource owner
        if ":" in resource:
            return resource.split(":", 1)[-1]
        return ""

    def filter_by_access(self, user: User, documents: List[Document]) -> List[Document]:
        """Filter list of documents to only those user can access.
        
        Args:
            user: The authenticated user
            documents: List of documents to filter
            
        Returns:
            Filtered list of accessible documents
        """
        accessible = [
            doc for doc in documents
            if self.can_access_document(user, doc)
        ]
        logger.info(
            f"Filtered {len(documents)} documents to {len(accessible)} "
            f"accessible documents for user {user.username}"
        )
        return accessible
