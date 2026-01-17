import sys
import asyncio
import logging
from datetime import timezone
from typing import Dict, Any, List

sys.path.insert(0, "/opt/airflow")

from src.config import get_settings
from src.services.indexing.factory import make_hybrid_indexing_service
from src.repositories.document import DocumentRepository
from src.database.factory import make_database

logger = logging.getLogger(__name__)


def index_documents_hybrid(**context) -> Dict[str, Any]:
    """
    Index parsed documents to OpenSearch with embeddings.
    
    This task:
    1. Pulls stored document IDs from XCom
    2. Fetches full document data from database
    3. Chunks and generates embeddings
    4. Indexes into OpenSearch
    
    :param context: Airflow task context
    :returns: Dictionary with indexing results
    """
    logger.info("Starting hybrid indexing")
    
    try:
        ti = context["ti"]
        document_ids = ti.xcom_pull(task_ids="parse_documents", key="stored_document_ids")
        
        if not document_ids:
            logger.info("No documents to index")
            return {"documents_indexed": 0, "chunks_created": 0}
        
        settings = get_settings()
        indexing_service = make_hybrid_indexing_service()
        database = make_database()
        
        # Fetch full document data
        with database.get_session() as session:
            document_repo = DocumentRepository(session)
            documents = []
            
            for doc_id in document_ids:
                doc = document_repo.get_by_document_id(doc_id)
                if doc:
                    documents.append({
                        "id": doc.id,
                        "document_id": doc.document_id,
                        "title": doc.title,
                        "department": doc.department,
                        "access_level": doc.access_level,
                        "owner_id": doc.owner_id,
                        "document_type": doc.document_type,
                        "file_path": doc.file_path,
                        "file_hash": doc.file_hash,
                        "version": doc.version,
                        "is_latest": doc.is_latest,
                        "content": doc.content,
                        "sections": doc.sections,
                        "created_at": doc.created_at,
                        "updated_at": doc.updated_at,
                        "expiry_date": doc.expiry_date
                    })
        
                if not documents:
                    logger.info("No document data found for indexing")
                    return {"documents_indexed": 0, "chunks_created": 0}
            
            logger.info(f"Indexing {len(documents)} documents to OpenSearch")
            
            # Run async indexing
            results = asyncio.run(_index_documents_async(
                documents=documents,
                indexing_service=indexing_service
            ))
            
            logger.info(f"Indexing complete: {results['documents_processed']} processed, "
                       f"{results['total_chunks_indexed']} chunks indexed")
            
            return results
            
    except Exception as e:
        logger.error(f"Indexing failed: {e}", exc_info=True)
        raise


async def _index_documents_async(documents: List[Dict], indexing_service) -> Dict[str, Any]:
    """
    Index documents asynchronously.
    """
    results = await indexing_service.index_documents_batch(
        documents=documents,
        replace_existing=True  # Replace old chunks if re-indexing
    )
    return results

