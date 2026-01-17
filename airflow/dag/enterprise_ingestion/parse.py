import sys
import asyncio
import logging
from typing import Dict, Any, List

sys.path.insert(0, "/opt/airflow")

from src.config import get_settings
from src.services.pdf_parser.factory import make_pdf_parser_service
from src.repositories.document import DocumentRepository
from src.schemas.document.document import DocumentCreate
from src.database.factory import make_database

logger = logging.getLogger(__name__)


def parse_documents(**context) -> Dict[str, Any]:
    """
    Parse clean documents and extract text content.
    
    This task:
    1. Pulls clean documents from XCom
    2. Parses each document (PDF, DOCX, etc.)
    3. Stores document metadata and content to database
    
    :param context: Airflow task context
    :returns: Dictionary with parsing results
    """
    logger.info("Starting document parsing")
    
    try:
        ti = context["ti"]
        clean_documents = ti.xcom_pull(task_ids="validate_documents", key="valid_documents")
        
        if not clean_documents:
            logger.info("No documents to parse")
            return {"documents_parsed": 0, "stored_documents": []}
        
        settings = get_settings()
        pdf_parser = make_pdf_parser_service()
        database = make_database()
        
        # Run async parsing
        results = asyncio.run(_parse_documents_async(
            documents=clean_documents,
            pdf_parser=pdf_parser,
            database=database,
            settings=settings  # FIX: Pass settings to async function
        ))
        
        logger.info(f"Parsing complete: {results['documents_parsed']} parsed, "
                   f"{results['documents_stored']} stored")
        
        return results
        
    except Exception as e:
        logger.error(f"Document parsing failed: {e}", exc_info=True)
        raise


async def _parse_documents_async(
    documents: List[Dict], 
    pdf_parser, 
    database,
    settings  # FIX: Add settings parameter
) -> Dict[str, Any]:
    """
    Parse documents asynchronously.
    Delegates to the same pattern as metadata_fetcher.py
    """
    results = {
        "documents_parsed": 0,
        "parse_failures": [],
        "documents_stored": []
    }
    
    # Use semaphore to control concurrent parsing
    parse_semaphore = asyncio.Semaphore(
        settings.enterprise_source.max_concurrent_parsing
    )
    
    async def parse_single_document(doc_meta: Dict) -> tuple:
        async with parse_semaphore:
            try:
                file_path = doc_meta["file_path"]
                parsed_content = await pdf_parser.parse_pdf(file_path)
                return (True, doc_meta, parsed_content)
            except Exception as e:
                logger.error(f"Parse failed for {doc_meta['document_id']}: {e}")
                return (False, doc_meta, None)
    
    # Parse all documents
    parse_tasks = [parse_single_document(doc) for doc in documents]
    parse_results = await asyncio.gather(*parse_tasks)
    
    # Store successful parses to database
    with database.get_session() as session:
        document_repo = DocumentRepository(session)
        
        for success, doc_meta, parsed_content in parse_results:
            if success and parsed_content:
                try:
                    # Create document record
                    document_create = DocumentCreate(
                        title=doc_meta["title"],
                        department=doc_meta["department"],
                        access_level=doc_meta["access_level"],
                        owner_id=doc_meta["owner_id"],
                        document_type=doc_meta["document_type"],
                        file_path=doc_meta["file_path"],
                        file_hash=doc_meta["file_hash"],
                        content=parsed_content.raw_text,
                        sections=[{"title": s.title, "content": s.content} for s in parsed_content.sections],
                        parser_used=parsed_content.parser_used.value,
                        parser_metadata=parsed_content.metadata,
                        expiry_date=doc_meta.get("expiry_date")
                    )
                    
                    document = document_repo.create(document_create)
                    results["documents_stored"].append(document.document_id)
                    results["documents_parsed"] += 1
                    
                except Exception as e:
                    logger.error(f"Failed to store document {doc_meta['document_id']}: {e}")
                    results["parse_failures"].append({
                        "document_id": doc_meta["document_id"],
                        "error": str(e)
                    })
            else:
                results["parse_failures"].append({
                    "document_id": doc_meta["document_id"],
                    "error": "Parsing failed"
                })
    
    # Push stored document IDs to XCom
    ti = context["ti"]
    ti.xcom_push(key="stored_document_ids", value=results["documents_stored"])
    
    return results

