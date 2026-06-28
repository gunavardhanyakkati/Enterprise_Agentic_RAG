from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    """Schema for enterprise document metadata."""

    document_id: str = Field(..., description="Unique document identifier")
    title: str = Field(..., description="Document title")
    owner_id: str = Field(..., description="ID of the document owner")
    contributors: List[str] = Field(default_factory=list, description="List of contributor IDs")
    description: str = Field(..., description="Document description/summary")
    department: str = Field(..., description="Owning department")
    access_level: Literal["public", "internal", "confidential", "restricted"] = Field(
        ..., description="Document access classification"
    )
    document_type: str = Field(..., description="Document type (e.g., policy, report, technical)")
    file_path: str = Field(..., description="Storage path to the document file")
    file_hash: str = Field(..., description="SHA256 hash of the file for integrity")
    version: int = Field(default=1, description="Document version number")
    is_latest: bool = Field(default=True, description="Whether this is the latest version")
    parent_version_id: Optional[str] = Field(None, description="ID of the previous version")
    created_by: str = Field(..., description="ID of the user who created the document")
    last_modified_by: str = Field(..., description="ID of the user who last modified")
    expiry_date: Optional[datetime] = Field(None, description="Document expiration date")


class DocumentBase(BaseModel):
    """Base schema for enterprise documents."""

    # Core metadata
    document_id: str = Field(..., description="Unique document identifier")
    title: str = Field(..., description="Document title")
    owner_id: str = Field(..., description="ID of the document owner")
    contributors: List[str] = Field(default_factory=list, description="List of contributor IDs")
    description: str = Field(..., description="Document description/summary")
    department: str = Field(..., description="Owning department")
    access_level: Literal["public", "internal", "confidential", "restricted"] = Field(
        ..., description="Document access classification"
    )
    document_type: str = Field(..., description="Document type (e.g., policy, report, technical)")
    file_path: str = Field(..., description="Storage path to the document file")
    file_hash: str = Field(..., description="SHA256 hash of the file for integrity")
    version: int = Field(default=1, description="Document version number")
    is_latest: bool = Field(default=True, description="Whether this is the latest version")
    parent_version_id: Optional[str] = Field(None, description="ID of the previous version")
    created_by: str = Field(..., description="ID of the user who created the document")
    last_modified_by: str = Field(..., description="ID of the user who last modified")
    expiry_date: Optional[datetime] = Field(None, description="Document expiration date")


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

    # Enterprise intelligence
    summary: Optional[str] = Field(None, description="Executive summary")
    classification_confidence: Optional[float] = Field(None, description="Classification confidence")
    extracted_metadata: Optional[Dict[str, Any]] = Field(None, description="Type-specific extracted metadata")
    compliance_report: Optional[Dict[str, Any]] = Field(None, description="Compliance analysis report")
    agent_executions: Optional[List[Dict[str, Any]]] = Field(None, description="Agent workflow telemetry")

    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class DocumentVersion(BaseModel):
    """Schema for document version information."""

    document_id: str = Field(..., description="Base document identifier")
    version: int = Field(..., description="Version number")
    is_latest: bool = Field(..., description="Whether this is the latest version")
    created_at: datetime = Field(..., description="Version creation timestamp")
    created_by: str = Field(..., description="User who created this version")
    change_summary: Optional[str] = Field(None, description="Summary of changes in this version")
    parent_version_id: Optional[str] = Field(None, description="Previous version ID")


class DocumentSearchResponse(BaseModel):
    """Schema for document search results."""

    documents: List[DocumentResponse]
    total: int
    departments: List[str]
    access_levels: List[str]
