from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field

from .document import DocumentBase


class DocumentCreate(DocumentBase):
    """Schema for creating/uploading a new document."""
    
    # File content for processing
    file_content: Optional[bytes] = Field(None, description="Raw file content for initial processing")
    
    # Parsed content (optional - added when file is processed)
    raw_text: Optional[str] = Field(None, description="Full raw text extracted from document")
    sections: Optional[List[Dict[str, Any]]] = Field(None, description="List of sections with titles and content")
    references: Optional[List[Dict[str, Any]]] = Field(None, description="List of references if extracted")
    
    # Processing metadata
    parser_used: Optional[str] = Field(None, description="Which parser was used")
    parser_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional parser metadata")
    content_processed: bool = Field(default=False, description="Whether content was successfully processed")
    content_processing_date: Optional[datetime] = Field(None, description="When content was processed")
