"""
Document lifecycle management services for enterprise knowledge base.
Handles versioning, retention policies, and secure deletion for compliance.
"""

from .version_control_service import VersionControlService
from .retention_service import RetentionService
from .document_deletion_service import DocumentDeletionService

__all__ = [
    "VersionControlService",
    "RetentionService",
    "DocumentDeletionService",
]
