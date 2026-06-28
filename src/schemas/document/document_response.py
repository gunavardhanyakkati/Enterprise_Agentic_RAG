from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field

from .document import DocumentBase


class DocumentResponse(DocumentBase):
    """Schema for document API responses with all content."""

    id: UUID = Field(..., description="Database primary key")
    
    # Parsed content (optional fields)
    raw_text: Optional[str] = Field(None, description="Full raw text extracted from document")
    sections: Optional[List[Dict[str, Any]]] = Field(None, description="List of sections with titles and content")
    references: Optional[List[Dict[str, Any]]] = Field(None, description="List of references if extracted")
    
    # Processing metadata
    parser_used: Optional[str] = Field(None, description="Which parser was used")
    parser_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional parser metadata")
    content_processed: bool = Field(default=False, description="Whether content was successfully processed")
    content_processing_date: Optional[datetime] = Field(None, description="When content was processed")

    summary: Optional[str] = None
    classification_confidence: Optional[float] = None
    extracted_metadata: Optional[Dict[str, Any]] = None
    compliance_report: Optional[Dict[str, Any]] = None
    agent_executions: Optional[List[Dict[str, Any]]] = None

    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True
