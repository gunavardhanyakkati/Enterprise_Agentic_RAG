"""
Document ingestion orchestration service.
Replaces metadata_fetcher.py with enterprise security and validation.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from src.config import Settings
from src.exceptions import PipelineException
from src.repositories.document import DocumentRepository
from src.schemas.document.document import DocumentCreate
from src.services.document_sources.base_source import BaseDocumentSource, DocumentMetadata
from src.services.document_ingestion.document_validator import DocumentValidator
from src.services.document_ingestion.virus_scanner import VirusScannerService
from src.services.document_ingestion.pii_detector import PIIDetectorService
from src.services.pdf_parser.parser import PDFParserService

logger = logging.getLogger(__name__)


class DocumentIngestionService:
    """
    Enterprise document ingestion service.
    Orchestrates: scan → validate → virus scan → PII scan → parse → store → index
    """
    
    def __init__(
        self,
        source_client: BaseDocumentSource,
        document_validator: DocumentValidator,
        virus_scanner: VirusScannerService,
        pii_detector: PIIDetectorService,
        pdf_parser: PDFParserService,
        max_concurrent_downloads: int = 5,
        max_concurrent_parsing: int = 1,
        settings: Optional[Settings] = None,
    ):
        self.source_client = source_client
        self.document_validator = document_validator
        self.virus_scanner = virus_scanner
        self.pii_detector = pii_detector
        self.pdf_parser = pdf_parser
        self.max_concurrent_downloads = max_concurrent_downloads
        self.max_concurrent_parsing = max_concurrent_parsing
        
        if settings is None:
            from src.config import get_settings
            settings = get_settings()
        self.settings = settings
        
        logger.info(
            f"Document ingestion service initialized: "
            f"max_downloads={max_concurrent_downloads}, "
            f"max_parsing={max_concurrent_parsing}"
        )
    
    async def ingest_documents(
        self,
        since: Optional[datetime] = None,
        db_session: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Full ingestion pipeline: scan → validate → virus scan → PII scan → parse → store → index
        
        :param since: Optional datetime to filter for new/modified documents
        :param db_session: Database session (required if store_to_db=True)
        :returns: Dictionary with ingestion statistics
        """
        results = {
            "documents_scanned": 0,
            "documents_validated": 0,
            "virus_scans_passed": 0,
            "pii_scans_passed": 0,
            "files_parsed": 0,
            "documents_stored": 0,
            "documents_indexed": 0,
            "errors": [],
            "processing_time": 0,
        }
        
        start_time = datetime.now()
        
        try:
            # Step 1: Scan source for documents
            logger.info("Step 1: Scanning document source")
            documents = await self.source_client.scan(since=since)
            results["documents_scanned"] = len(documents)
            
            if not documents:
                logger.info("No documents found to process")
                return results
            
            # Step 2: Process documents through pipeline
            logger.info(f"Step 2: Processing {len(documents)} documents")
            pipeline_results = await self._process_documents_batch(documents)
            results.update(pipeline_results)
            
            # Step 3: Store to database (if session provided)
            if db_session and results["parsed_documents"]:
                logger.info("Step 3: Storing documents to database")
                stored_count = self._store_documents_to_db(
                    documents, results["parsed_documents"], db_session
                )
                results["documents_stored"] = stored_count
            
            # Calculate processing time
            results["processing_time"] = (datetime.now() - start_time).total_seconds()
            
            logger.info(
                f"Ingestion complete: {results['documents_scanned']} scanned, "
                f"{results['documents_stored']} stored in {results['processing_time']:.1f}s"
            )
            
            if results["errors"]:
                logger.warning(f"Ingestion errors ({len(results['errors'])}): {results['errors'][:5]}")
            
            return results
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            results["errors"].append(f"Pipeline error: {str(e)}")
            raise PipelineException(f"Ingestion pipeline failed: {e}") from e
    
    async def _process_documents_batch(
        self,
        documents: List[DocumentMetadata],
    ) -> Dict[str, Any]:
        """
        Process batch of documents with concurrent execution.
        Preserves async pipeline pattern from metadata_fetcher.py
        """
        results = {
            "documents_validated": 0,
            "virus_scans_passed": 0,
            "pii_scans_passed": 0,
            "files_parsed": 0,
            "parsed_documents": {},
            "errors": [],
            "validation_failures": [],
            "virus_failures": [],
            "pii_failures": [],
            "parse_failures": [],
        }
        
        # Create semaphores for controlled concurrency
        download_semaphore = asyncio.Semaphore(self.max_concurrent_downloads)
        parse_semaphore = asyncio.Semaphore(self.max_concurrent_parsing)
        
        # Create pipeline tasks (preserve pattern from metadata_fetcher.py)
        pipeline_tasks = [
            self._process_document_pipeline(
                document,
                download_semaphore,
                parse_semaphore,
            )
            for document in documents
        ]
        
        # Execute tasks with gather
        pipeline_results = await asyncio.gather(*pipeline_tasks, return_exceptions=True)
        
        # Process results (preserve tuple unpacking pattern)
        for document, result in zip(documents, pipeline_results):
            if isinstance(result, Exception):
                error_msg = f"Pipeline error for {document.document_id}: {str(result)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
                continue
            
            if result:
                validation_success, virus_success, pii_success, parse_success, parsed_doc = result
                
                if validation_success:
                    results["documents_validated"] += 1
                
                if virus_success:
                    results["virus_scans_passed"] += 1
                else:
                    results["virus_failures"].append(document.document_id)
                
                if pii_success:
                    results["pii_scans_passed"] += 1
                else:
                    results["pii_failures"].append(document.document_id)
                
                if parse_success and parsed_doc:
                    results["files_parsed"] += 1
                    results["parsed_documents"][str(document.document_id)] = parsed_doc
                else:
                    results["parse_failures"].append(document.document_id)
            else:
                results["validation_failures"].append(document.document_id)
        
        return results
    
    async def _process_document_pipeline(
        self,
        document: DocumentMetadata,
        download_semaphore: asyncio.Semaphore,
        parse_semaphore: asyncio.Semaphore,
    ) -> Optional[tuple]:
        """
        Individual document processing pipeline.
        Returns tuple of (validation_success, virus_success, pii_success, parse_success, parsed_doc)
        """
        local_path = None
        
        try:
            # Step 1: Validate document
            is_valid, error_msg = self.document_validator.validate_file(Path(document.file_path))
            if not is_valid:
                logger.warning(f"Validation failed for {document.document_id}: {error_msg}")
                return None
            
            # Step 2: Download file (with semaphore concurrency control)
            async with download_semaphore:
                local_path = await self.source_client.download(document)
                if not local_path:
                    logger.error(f"Download failed for {document.document_id}")
                    return (True, False, False, False, None)
            
            # Step 3: Virus scan
            scan_clean, virus_name = await self.virus_scanner.scan_file(local_path)
            if not scan_clean:
                logger.warning(f"Virus detected in {document.document_id}: {virus_name}")
                # Clean up infected file
                local_path.unlink(missing_ok=True)
                return (True, False, False, False, None)
            
            # Step 4: PII scan
            pii_findings = await self.pii_detector.scan_file(local_path)
            if pii_findings:
                # Generate report for compliance
                report = self.pii_detector.generate_report(pii_findings)
                logger.warning(f"PII detected in {document.document_id}: {report}")
                # For now, just log - could block ingestion based on policy
            
            # Step 5: Parse document (with semaphore concurrency control)
            async with parse_semaphore:
                parsed_content = await self.pdf_parser.parse_pdf(local_path)
                if not parsed_content:
                    logger.warning(f"Parsing failed for {document.document_id}")
                    return (True, True, True, False, None)
            
            # Clean up downloaded file after successful parse
            if local_path:
                local_path.unlink(missing_ok=True)
            
            return (True, True, True, True, parsed_content)
            
        except Exception as e:
            logger.error(f"Pipeline error for {document.document_id}: {e}")
            raise
        finally:
            # Ensure temp file is cleaned up
            if local_path and local_path.exists():
                local_path.unlink(missing_ok=True)
    
    def _store_documents_to_db(
        self,
        documents: List[DocumentMetadata],
        parsed_documents: dict,
        db_session: Session,
    ) -> int:
        """
        Store documents and parsed content to database.
        Preserves upsert pattern from paper repository.
        """
        document_repo = DocumentRepository(db_session)
        stored_count = 0
        
        for document in documents:
            try:
                # Get parsed content if available
                parsed_content = parsed_documents.get(str(document.document_id))
                
                # Create document record
                document_create = DocumentCreate(
                    document_id=document.document_id,
                    title=document.title,
                    department=document.department,
                    access_level=document.access_level or "internal",
                    document_type=document.document_type or "unknown",
                    owner_id=document.owner_id or "system",
                    created_by=document.owner_id or "system",
                    last_modified_by=document.owner_id or "system",
                    file_path=document.file_path,
                    file_hash=document.file_hash,
                    expiry_date=None,  # Set by retention policy
                    content=parsed_content.raw_text if parsed_content else None,
                    sections=parsed_content.sections if parsed_content else None,
                    parser_used=parsed_content.parser_used.value if parsed_content else None,
                    parser_metadata=parsed_content.metadata if parsed_content else None,
                )
                
                # Upsert pattern (check existence → update or create)
                document = document_repo.upsert(document_create)
                if document:
                    stored_count += 1
                    logger.debug(f"Stored document {document.document_id}")
                
            except Exception as e:
                logger.error(f"Failed to store document {document.document_id}: {e}")
        
        # Commit transaction
        try:
            db_session.commit()
            logger.info(f"Committed {stored_count} documents to database")
        except Exception as e:
            logger.error(f"Failed to commit documents: {e}")
            db_session.rollback()
            stored_count = 0
        
        return stored_count

