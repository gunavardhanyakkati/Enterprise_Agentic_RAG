"""
Document versioning service for enterprise knowledge base.
Manages document versions, creation, retrieval, and rollback.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.models.document import Document
from src.repositories.document import DocumentRepository
from src.schemas.document.document import DocumentCreate

logger = logging.getLogger(__name__)


class VersionControlService:
    """
    Manages document versioning for enterprise knowledge base.
    Creates new versions on updates, tracks history, and supports rollback.
    """
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.document_repo = DocumentRepository(db_session)
        
        logger.info("Version control service initialized")
    
    def create_version(self, document_id: UUID, updated_data: dict) -> Document:
        """
        Create a new version of an existing document.
        Marks current version as not latest, creates new version record.
        
        :param document_id: ID of document to version
        :param updated_data: Updated document data
        :returns: New version document instance
        """
        try:
            # Get current latest version
            current_version = self.document_repo.get_latest_version(document_id)
            if not current_version:
                raise ValueError(f"Document {document_id} not found")
            
            # Mark current version as not latest
            current_version.is_latest = False
            current_version.updated_at = datetime.now(timezone.utc)
            self.document_repo.update(current_version)
            
            # Create new version
            new_version = DocumentCreate(
                document_id=document_id,  # Same ID for version group
                title=updated_data.get("title", current_version.title),
                department=updated_data.get("department", current_version.department),
                access_level=updated_data.get("access_level", current_version.access_level),
                document_type=updated_data.get("document_type", current_version.document_type),
                owner_id=updated_data.get("owner_id", current_version.owner_id),
                created_by=updated_data.get("created_by", current_version.created_by),
                last_modified_by=updated_data.get("last_modified_by", current_version.last_modified_by),
                file_path=updated_data.get("file_path", current_version.file_path),
                file_hash=updated_data.get("file_hash", current_version.file_hash),
                expiry_date=updated_data.get("expiry_date", current_version.expiry_date),
                content=updated_data.get("content", current_version.content),
                sections=updated_data.get("sections", current_version.sections),
                parser_used=updated_data.get("parser_used", current_version.parser_used),
                parser_metadata=updated_data.get("parser_metadata", current_version.parser_metadata),
                version=current_version.version + 1,  # Increment version
                is_latest=True,
                parent_version_id=current_version.id,  # Link to parent
            )
            
            # Create new version record
            new_document = self.document_repo.create(new_version)
            
            logger.info(
                f"Created version {new_document.version} for document {document_id} "
                f"(parent: {current_version.version})"
            )
            
            return new_document
            
        except Exception as e:
            logger.error(f"Error creating version: {e}")
            self.db_session.rollback()
            raise
    
    def get_version_history(self, document_id: UUID) -> List[Document]:
        """
        Get complete version history for a document.
        Returns versions in descending order (newest first).
        
        :param document_id: Document ID
        :returns: List of document versions
        """
        try:
            versions = self.document_repo.get_versions(document_id)
            logger.info(f"Retrieved {len(versions)} versions for document {document_id}")
            return versions
            
        except Exception as e:
            logger.error(f"Error retrieving version history: {e}")
            raise
    
    def get_version(self, document_id: UUID, version: int) -> Optional[Document]:
        """
        Get specific version of a document.
        
        :param document_id: Document ID
        :param version: Version number
        :returns: Document instance or None
        """
        try:
            versions = self.get_version_history(document_id)
            for doc in versions:
                if doc.version == version:
                    logger.info(f"Retrieved version {version} for document {document_id}")
                    return doc
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving version {version}: {e}")
            raise
    
    def rollback_to_version(self, document_id: UUID, target_version: int) -> Document:
        """
        Rollback document to a specific version.
        Creates new version with content from target version.
        
        :param document_id: Document ID
        :param target_version: Version to rollback to
        :returns: New current version
        """
        try:
            # Get target version data
            target_doc = self.get_version(document_id, target_version)
            if not target_doc:
                raise ValueError(f"Version {target_version} not found for document {document_id}")
            
            # Create new version with target data
            version_data = {
                "content": target_doc.content,
                "sections": target_doc.sections,
                "parser_used": target_doc.parser_used,
                "parser_metadata": target_doc.parser_metadata,
                "file_hash": target_doc.file_hash,
                "last_modified_by": f"rollback_from_v{target_version}",
            }
            
            new_version = self.create_version(document_id, version_data)
            
            logger.info(
                f"Rolled back document {document_id} to version {target_version}, "
                f"created new version {new_version.version}"
            )
            
            return new_version
            
        except Exception as e:
            logger.error(f"Error during rollback: {e}")
            self.db_session.rollback()
            raise
    
    def cleanup_old_versions(self, document_id: UUID, keep_versions: int = 10) -> int:
        """
        Remove old versions keeping only the specified number.
        Always keeps the latest version.
        
        :param document_id: Document ID
        :param keep_versions: Number of versions to keep
        :returns: Number of versions deleted
        """
        try:
            versions = self.get_version_history(document_id)
            
            if len(versions) <= keep_versions:
                logger.info(f"No versions to cleanup for document {document_id}")
                return 0
            
            # Sort by version number (ascending)
            versions.sort(key=lambda x: x.version)
            
            # Keep latest and specified number of recent versions
            versions_to_delete = versions[:-keep_versions]
            
            deleted_count = 0
            for version in versions_to_delete:
                # Never delete the latest version
                if version.is_latest:
                    continue
                
                self.db_session.delete(version)
                deleted_count += 1
            
            self.db_session.commit()
            
            logger.info(
                f"Cleaned up {deleted_count} old versions for document {document_id}, "
                f"kept {keep_versions} versions"
            )
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up versions: {e}")
            self.db_session.rollback()
            raise

