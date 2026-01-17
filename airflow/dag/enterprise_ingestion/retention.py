import sys
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

sys.path.insert(0, "/opt/airflow")

from src.config import get_settings
from src.repositories.document import DocumentRepository
from src.services.opensearch.client import OpenSearchClient
from src.database import make_database

logger = logging.getLogger(__name__)


def apply_retention_policy(**context) -> Dict[str, Any]:
    """
    Apply document retention policy.
    
    This task:
    1. Identifies documents past their expiry date
    2. Archives or deletes them based on policy
    3. Updates OpenSearch index
    
    :param context: Airflow task context
    :returns: Dictionary with retention results
    """
    logger.info("Starting retention policy enforcement")
    
    try:
        settings = get_settings()
        database = make_database()
        
        logger.info(f"Retention policy: {settings.document_lifecycle.retention_days} days")
        logger.info(f"Auto-archive: {settings.document_lifecycle.auto_archive_days} days")
        
        # Calculate cutoff date
        cutoff_date = datetime.now(timezone.utc) - timedelta(
            days=settings.document_lifecycle.retention_days
        )
        
        # Find expired documents
        with database.get_session() as session:
            document_repo = DocumentRepository(session)
            expired_docs = document_repo.get_expired_documents(cutoff_date)
            
            results = {
                "documents_checked": 0,
                "documents_archived": 0,
                "documents_deleted": 0,
                "errors": []
            }
            
            if not expired_docs:
                logger.info("No expired documents found")
                return results
            
            results["documents_checked"] = len(expired_docs)
            
            for doc in expired_docs:
                try:
                    # Check if should archive or delete
                    archive_cutoff = datetime.now(timezone.utc) - timedelta(
                        days=settings.document_lifecycle.auto_archive_days
                    )
                    
                    if doc.created_at < archive_cutoff:
                        # Delete permanently
                        document_repo.delete(doc.id)
                        results["documents_deleted"] += 1
                        logger.info(f"Deleted expired document: {doc.document_id}")
                    else:
                        # Archive (soft delete)
                        doc.is_active = False
                        document_repo.update(doc)
                        results["documents_archived"] += 1
                        logger.info(f"Archived expired document: {doc.document_id}")
                
                except Exception as e:
                    logger.error(f"Error processing document {doc.document_id}: {e}")
                    results["errors"].append(str(e))
            
            # Commit session
            session.commit()
            
            # Clean up OpenSearch index
            if results["documents_deleted"] > 0 or results["documents_archived"] > 0:
                logger.info("Cleaning up OpenSearch index for expired documents")
                opensearch_client = OpenSearchClient(
                    host=settings.opensearch.host,
                    settings=settings
                )
                deleted_chunks = opensearch_client.delete_expired_documents(
                    expiry_date=cutoff_date
                )
                results["opensearch_chunks_deleted"] = deleted_chunks
            
            logger.info(
                f"Retention policy complete: "
                f"{results['documents_archived']} archived, "
                f"{results['documents_deleted']} deleted"
            )
            
            return results
            
    except Exception as e:
        logger.error(f"Retention policy enforcement failed: {e}", exc_info=True)
        raise

