"""
Retention policy enforcement service for enterprise compliance.
Manages document lifecycle based on retention policies and expiry dates.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.config import Settings
from src.models.document import Document
from src.repositories.document import DocumentRepository
from src.services.opensearch.client import OpenSearchClient

logger = logging.getLogger(__name__)


class RetentionService:
    """
    Enforces document retention policies for compliance.
    Handles expiry, archival, and deletion based on configuration.
    """
    
    def __init__(
        self,
        db_session: Session,
        opensearch_client: Optional[OpenSearchClient] = None,
        settings: Optional[Settings] = None,
    ):
        self.db_session = db_session
        self.document_repo = DocumentRepository(db_session)
        self.opensearch_client = opensearch_client
        
        if settings is None:
            from src.config import get_settings
            settings = get_settings()
        self.settings = settings
        
        self.retention_days = settings.document_lifecycle.retention_days
        self.auto_archive_days = settings.document_lifecycle.auto_archive_days
        self.allow_permanent_delete = settings.document_lifecycle.allow_permanent_delete
        
        logger.info(
            f"Retention service initialized: "
            f"retention={self.retention_days} days, "
            f"auto_archive={self.auto_archive_days} days"
        )
    
    def enforce_retention_policy(self) -> dict:
        """
        Main retention policy enforcement.
        Finds expired documents and applies retention actions.
        
        :returns: Dict with action counts
        """
        results = {
            "expired_documents_found": 0,
            "documents_archived": 0,
            "documents_deleted": 0,
            "documents_soft_deleted": 0,
            "errors": [],
        }
        
        try:
            # Find expired documents
            expired_docs = self._find_expired_documents()
            results["expired_documents_found"] = len(expired_docs)
            
            if not expired_docs:
                logger.info("No expired documents found")
                return results
            
            logger.info(f"Found {len(expired_docs)} expired documents")
            
            # Apply retention actions
            for document in expired_docs:
                try:
                    action = self._apply_retention_action(document)
                    results[f"documents_{action}"] += 1
                    
                except Exception as e:
                    error_msg = f"Error processing document {document.document_id}: {e}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Retention enforcement error: {e}")
            results["errors"].append(str(e))
            return results
    
    def _find_expired_documents(self) -> List[Document]:
        """
        Find documents that have passed their expiry date.
        
        :returns: List of expired documents
        """
        try:
            expiry_threshold = datetime.now(timezone.utc)
            
            # Find documents with expiry_date in the past
            expired_docs = self.db_session.query(Document).filter(
                Document.expiry_date < expiry_threshold,
                Document.is_latest == True,
            ).all()
            
            logger.info(f"Found {len(expired_docs)} expired documents")
            return expired_docs
            
        except Exception as e:
            logger.error(f"Error finding expired documents: {e}")
            raise
    
    def _find_stale_documents(self) -> List[Document]:
        """
        Find documents that haven't been modified in auto_archive_days.
        
        :returns: List of stale documents
        """
        try:
            stale_threshold = datetime.now(timezone.utc) - timedelta(days=self.auto_archive_days)
            
            # Find documents not modified in specified days
            stale_docs = self.db_session.query(Document).filter(
                Document.updated_at < stale_threshold,
                Document.is_latest == True,
                Document.expiry_date.is_(None),  # Don't archive already expired docs
            ).all()
            
            logger.info(f"Found {len(stale_docs)} stale documents")
            return stale_docs
            
        except Exception as e:
            logger.error(f"Error finding stale documents: {e}")
            raise
    
    def _apply_retention_action(self, document: Document) -> str:
        """
        Apply appropriate retention action based on policy.
        
        :param document: Document to process
        :returns: Action taken (archived/deleted/soft_deleted)
        """
        try:
            # Determine how long ago document expired
            days_expired = (datetime.now(timezone.utc) - document.expiry_date).days
            
            if days_expired > self.retention_days:
                # Retention period exceeded - delete
                if self.allow_permanent_delete:
                    self._permanent_delete(document)
                    return "deleted"
                else:
                    self._soft_delete(document)
                    return "soft_deleted"
            else:
                # Within retention period - archive
                self._archive_document(document)
                return "archived"
                
        except Exception as e:
            logger.error(f"Error applying retention action to {document.document_id}: {e}")
            raise
    
    def _archive_document(self, document: Document):
        """
        Archive a document (mark as archived but keep in database).
        """
        try:
            document.is_latest = False
            document.parser_metadata = document.parser_metadata or {}
            document.parser_metadata["archived_at"] = datetime.now(timezone.utc).isoformat()
            
            self.document_repo.update(document)
            
            # Also update in OpenSearch if available
            if self.opensearch_client:
                self.opensearch_client.update_document_access(
                    str(document.document_id),
                    access_level="archived"
                )
            
            logger.info(f"Archived document {document.document_id}")
            
        except Exception as e:
            logger.error(f"Error archiving document {document.document_id}: {e}")
            raise
    
    def _soft_delete(self, document: Document):
        """
        Soft delete a document (mark as deleted but keep in database).
        """
        try:
            document.is_latest = False
            document.parser_metadata = document.parser_metadata or {}
            document.parser_metadata["soft_deleted_at"] = datetime.now(timezone.utc).isoformat()
            
            self.document_repo.update(document)
            
            # Update in OpenSearch
            if self.opensearch_client:
                self.opensearch_client.update_document_access(
                    str(document.document_id),
                    access_level="deleted"
                )
            
            logger.info(f"Soft deleted document {document.document_id}")
            
        except Exception as e:
            logger.error(f"Error soft deleting document {document.document_id}: {e}")
            raise
    
    def _permanent_delete(self, document: Document):
        """
        Permanently delete a document from database and OpenSearch.
        """
        try:
            if not self.allow_permanent_delete:
                raise PermissionError("Permanent deletion is disabled by policy")
            
            document_id = str(document.document_id)
            
            # Delete from database
            self.db_session.delete(document)
            
            # Delete from OpenSearch
            if self.opensearch_client:
                deleted_count = self.opensearch_client.delete_document_chunks(document_id)
                logger.info(f"Deleted {deleted_count} chunks from OpenSearch for {document_id}")
            
            logger.warning(f"PERMANENTLY DELETED document {document_id}")
            
        except Exception as e:
            logger.error(f"Error permanently deleting document {document.document_id}: {e}")
            raise
    
    def set_expiry_date(self, document_id: str, expiry_date: datetime):
        """
        Set or update document expiry date.
        
        :param document_id: Document ID
        :param expiry_date: New expiry date
        """
        try:
            document = self.document_repo.get_by_document_id(document_id)
            if not document:
                raise ValueError(f"Document {document_id} not found")
            
            document.expiry_date = expiry_date
            document.updated_at = datetime.now(timezone.utc)
            
            self.document_repo.update(document)
            
            logger.info(f"Set expiry date for document {document_id}: {expiry_date}")
            
        except Exception as e:
            logger.error(f"Error setting expiry date for {document_id}: {e}")
            self.db_session.rollback()
            raise

