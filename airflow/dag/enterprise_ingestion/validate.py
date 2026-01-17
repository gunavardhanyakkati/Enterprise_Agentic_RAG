import sys
import logging
from typing import Dict, Any, List

sys.path.insert(0, "/opt/airflow")

from src.config import get_settings
from src.services.document_ingestion.document_validator import DocumentValidator

logger = logging.getLogger(__name__)


def validate_documents(**context) -> Dict[str, Any]:
    """
    Validate document metadata and files.
    
    This task:
    1. Pulls document metadata from XCom
    2. Validates file size, MIME type, and integrity
    3. Filters out invalid documents
    
    :param context: Airflow task context
    :returns: Dictionary with validation results
    """
    logger.info("Starting document validation")
    
    try:
        ti = context["ti"]
        document_metadata = ti.xcom_pull(task_ids="scan_sources", key="document_metadata")
        
        if not document_metadata:
            logger.info("No documents to validate")
            return {"documents_validated": 0, "valid_documents": []}
        
        settings = get_settings()
        validator = DocumentValidator(
            supported_mime_types=settings.file_processing.supported_mime_types,
            max_file_size_mb=settings.file_processing.max_file_size_mb
        )
        
        results = {
            "documents_validated": len(document_metadata),
            "valid_documents": [],
            "invalid_documents": []
        }
        
        for doc_meta in document_metadata:
            try:
                file_path = doc_meta.get("file_path")
                if not file_path:
                    raise ValueError("Missing file_path in metadata")
                
                # Validate file
                is_valid, error_msg = validator.validate_file(file_path)
                
                if is_valid:
                    # Add extracted metadata
                    extracted_meta = validator.extract_metadata(file_path)
                    doc_meta.update(extracted_meta)
                    results["valid_documents"].append(doc_meta)
                    logger.debug(f"Document {doc_meta['document_id']} validated successfully")
                else:
                    results["invalid_documents"].append({
                        "document_id": doc_meta["document_id"],
                        "error": error_msg
                    })
                    logger.warning(f"Document {doc_meta['document_id']} validation failed: {error_msg}")
            
            except Exception as e:
                logger.error(f"Error validating document {doc_meta.get('document_id')}: {e}")
                results["invalid_documents"].append({
                    "document_id": doc_meta.get("document_id"),
                    "error": str(e)
                })
        
        logger.info(f"Validation complete: {len(results['valid_documents'])} valid, "
                   f"{len(results['invalid_documents'])} invalid")
        
        # Push valid documents to XCom
        ti.xcom_push(key="valid_documents", value=results["valid_documents"])
        
        return results
        
    except Exception as e:
        logger.error(f"Document validation failed: {e}", exc_info=True)
        raise
