from functools import lru_cache
from typing import Optional, Union

from src.config import get_settings

from .office_parser import OfficeParser
from .parser import PDFParserService


@lru_cache(maxsize=3)
def make_pdf_parser_service(mime_type: Optional[str] = None) -> Union[PDFParserService, OfficeParser]:
    """Create cached parser service based on MIME type.
    
    This factory routes to the appropriate parser based on the document's MIME type.
    For backward compatibility, when mime_type is None, returns PDF parser.
    
    Args:
        mime_type: Optional MIME type. If None, returns PDF parser.
        
    Returns:
        Parser service instance for the given MIME type.
        
    Supported MIME types:
    - application/pdf: PDF documents (uses Docling)
    - application/vnd.openxmlformats-officedocument.*: Office documents (.docx, .pptx, .xlsx)
    - application/msword, application/vnd.ms-*: Legacy Office documents (.doc, .ppt, .xls)
    """
    settings = get_settings()
    
    # Default behavior: return PDF parser for backward compatibility
    if mime_type is None:
        logger.debug("Creating PDF parser service (default)")
        return PDFParserService(
            max_pages=settings.pdf_parser.max_pages,
            max_file_size_mb=settings.pdf_parser.max_file_size_mb,
            do_ocr=settings.pdf_parser.do_ocr,
            do_table_structure=settings.pdf_parser.do_table_structure,
        )
    
    logger.info(f"Creating parser service for MIME type: {mime_type}")
    
    # PDF documents
    if mime_type == "application/pdf":
        return PDFParserService(
            max_pages=settings.pdf_parser.max_pages,
            max_file_size_mb=settings.pdf_parser.max_file_size_mb,
            do_ocr=settings.pdf_parser.do_ocr,
            do_table_structure=settings.pdf_parser.do_table_structure,
        )
    
    # Office documents
    if mime_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # .pptx
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
        "application/msword",  # .doc
        "application/vnd.ms-powerpoint",  # .ppt
        "application/vnd.ms-excel",  # .xls
    ):
        logger.info("Creating Office document parser")
        return OfficeParser()
    
    # Unknown type - fallback to PDF parser (will fail gracefully if file is not PDF)
    logger.warning(f"Unknown MIME type '{mime_type}', falling back to PDF parser")
    return PDFParserService(
        max_pages=settings.pdf_parser.max_pages,
        max_file_size_mb=settings.pdf_parser.max_file_size_mb,
        do_ocr=settings.pdf_parser.do_ocr,
        do_table_structure=settings.pdf_parser.do_table_structure,
    )
