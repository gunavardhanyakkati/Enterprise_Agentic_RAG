import sys
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

sys.path.insert(0, "/opt/airflow")

from src.config import get_settings
from src.services.document_sources.factory import make_document_source

logger = logging.getLogger(__name__)


def scan_sources(**context) -> Dict[str, Any]:
    """
    Scan enterprise document sources for new or modified files.
    
    This task:
    1. Connects to configured source (S3, SharePoint, Filesystem)
    2. Scans for documents modified since last run
    3. Returns metadata for documents to process
    
    :param context: Airflow task context
    :returns: Dictionary with scan results
    """
    logger.info("Starting enterprise document source scan")
    
    try:
        settings = get_settings()
        source_client = make_document_source(settings)
        
        # Validate source connectivity
        if not source_client.validate_source():
            raise Exception("Document source validation failed")
        
        # Scan for documents modified in last 4 hours (or since last run)
        execution_date = context.get("execution_date")
        if execution_date:
            since = execution_date - timedelta(hours=4)
        else:
            since = datetime.now(timezone.utc) - timedelta(hours=4)
        
        logger.info(f"Scanning for documents modified since: {since.isoformat()}")
        
        documents = source_client.scan(since=since)
        logger.info(f"Found {len(documents)} documents to process")
        
        # Prepare results
        results = {
            "documents_found": len(documents),
            "documents": [doc.model_dump() for doc in documents],
            "scan_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Push to XCom for downstream tasks
        ti = context["ti"]
        ti.xcom_push(key="documents_found", value=len(documents))
        ti.xcom_push(key="document_metadata", value=results["documents"])
        
        logger.info("Scan completed successfully")
        return results
        
    except Exception as e:
        logger.error(f"Source scan failed: {e}", exc_info=True)
        raise
