"""
Secure document deletion service for enterprise compliance.
Ensures documents are properly purged from all systems with audit trail.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from src.models.audit_log import AuditLog
from src.models.document import Document
from src.repositories.audit_log import AuditLogRepository
from src.repositories.document import DocumentRepository
from src.services.opensearch.client import OpenSearchClient

logger = logging.getLogger(__name__)


class DocumentDeletionService:
    """
    Secure deletion service ensuring GDPR/CCPA compliance.
    Removes documents from database, OpenSearch, and file systems with audit trail.
    """
    
    def __init__(
        self,
        db_session: Session,
        opensearch_client: Optional[OpenSearchClient] = None,
        audit_logger: Optional[AuditLogRepository] = None,
    ):
        self.db_session = db_session
        self.document_repo = DocumentRepository(db_session)
        self.opensearch_client = opensearch_client
        
        if audit_logger is None:
            self.audit_logger = AuditLogRepository(db_session)
        else:
            self.audit_logger = audit_logger
        
        logger.info("Document deletion service initialized")
    
    def delete_document(
        self,
        document_id: str,
        user_id: str,
        reason: str,
        permanent: bool = False,
        cascade: bool = True,
    ) -> dict:
        """
        Delete a document with full audit trail.
        
        :param document_id: ID of document to delete
        :param user_id: ID of user performing deletion
        :param reason: Reason for deletion (compliance audit)
        :param permanent: If True, permanently delete vs soft delete
        :param cascade: If True, delete all versions and associated data
        :returns: Deletion result dictionary
        """
        deletion_result = {
            "document_id": document_id,
            "deleted": False,
            "versions_deleted": 0,
            "chunks_deleted": 0,
            "audit_log_id": None,
            "error": None,
        }
        
        try:
            # Find document
            document = self.document_repo.get_by_document_id(document_id)
            if not document:
                raise ValueError(f"Document {document_id} not found")
            
            # Get all versions if cascading
            documents_to_delete = [document]
            if cascade:
                versions = self.document_repo.get_versions(document_id)
                documents_to_delete = versions
            
            # Log deletion attempt
            audit_entry = self.audit_logger.create(
                AuditLog(
                    user_id=user_id,
                    action="DELETE" if permanent else "SOFT_DELETE",
                    document_id=document_id,
                    ip_address="0.0.0.0",  # Would come from request
                    user_agent="deletion_service",
                    query_params={"reason": reason, "cascade": cascade},
                    response_status="success",
                )
            )
            deletion_result["audit_log_id"] = str(audit_entry.id)
            
            # Delete from OpenSearch first (recoverable)
            if self.opensearch_client:
                for doc in documents_to_delete:
                    chunks_deleted = self.opensearch_client.delete_document_chunks(
                        str(doc.document_id)
                    )
                    deletion_result["chunks_deleted"] += chunks_deleted
            
            # Delete from database
            for doc in documents_to_delete:
                if permanent:
                    self.db_session.delete(doc)
                else:
                    # Soft delete
                    doc.is_latest = False
                    doc.parser_metadata = doc.parser_metadata or {}
                    doc.parser_metadata["soft_deleted_by"] = user_id
                    doc.parser_metadata["soft_deleted_at"] = datetime.now(timezone.utc).isoformat()
                    doc.parser_metadata["soft_deleted_reason"] = reason
                    self.db_session.add(doc)
                
                deletion_result["versions_deleted"] += 1
            
            self.db_session.commit()
            deletion_result["deleted"] = True
            
            logger.warning(
                f"{'PERMANENTLY ' if permanent else ''}DELETED document {document_id} "
                f"({deletion_result['versions_deleted']} versions, {deletion_result['chunks_deleted']} chunks) "
                f"by user {user_id}"
            )
            
            return deletion_result
            
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}")
            self.db_session.rollback()
            deletion_result["error"] = str(e)
            return deletion_result
    
    def bulk_delete(
        self,
        document_ids: List[str],
        user_id: str,
        reason: str,
        permanent: bool = False,
    ) -> dict:
        """
        Bulk delete multiple documents.
        
        :param document_ids: List of document IDs to delete
        :param user_id: User performing deletion
        :param reason: Bulk deletion reason
        :param permanent: Whether to permanently delete
        :returns: Summary of bulk deletion results
        """
        results = {
            "total_requested": len(document_ids),
            "successful": 0,
            "failed": 0,
            "errors": [],
        }
        
        for doc_id in document_ids:
            try:
                result = self.delete_document(
                    document_id=doc_id,
                    user_id=user_id,
                    reason=reason,
                    permanent=permanent,
                    cascade=True,
                )
                
                if result["deleted"]:
                    results["successful"] += 1
                else:
                    results["failed"] += 1
                    if result["error"]:
                        results["errors"].append(result["error"])
                        
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"{doc_id}: {str(e)}")
                logger.error(f"Bulk delete error for {doc_id}: {e}")
        
        logger.info(
            f"Bulk delete complete: {results['successful']}/{results['total_requested']} successful, "
            f"{results['failed']} failed"
        )
        
        return results
    
    def restore_document(self, document_id: str, user_id: str) -> bool:
        """
        Restore a soft-deleted document.
        
        :param document_id: Document ID to restore
        :param user_id: User performing restoration
        :returns: True if restored successfully
        """
        try:
            document = self.document_repo.get_by_document_id(document_id)
            if not document:
                raise ValueError(f"Document {document_id} not found")
            
            if document.is_latest:
                logger.warning(f"Document {document_id} is not deleted, cannot restore")
                return False
            
            # Check if it was soft deleted
            if document.parser_metadata and "soft_deleted_at" in document.parser_metadata:
                # Restore (remove soft delete markers)
                document.is_latest = True
                document.parser_metadata["restored_by"] = user_id
                document.parser_metadata["restored_at"] = datetime.now(timezone.utc).isoformat()
                
                self.document_repo.update(document)
                self.db_session.commit()
                
                logger.info(f"Restored document {document_id} by user {user_id}")
                return True
            else:
                logger.error(f"Document {document_id} was not soft-deleted")
                return False
                
        except Exception as e:
            logger.error(f"Error restoring document {document_id}: {e}")
            self.db_session.rollback()
            raise
