from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime

class AuditLogBase(BaseModel):
    """Base audit log schema with common fields."""
    user_id: UUID = Field(..., description="ID of the user who performed the action")
    action: str = Field(
        ..., 
        pattern="^(VIEW|DOWNLOAD|SEARCH|UPLOAD|EDIT|DELETE)$",
        description="Action performed: VIEW, DOWNLOAD, SEARCH, UPLOAD, EDIT, DELETE"
    )
    document_id: Optional[UUID] = Field(None, description="ID of the document affected (if applicable)")
    ip_address: Optional[str] = Field(None, description="IP address of the user")
    user_agent: Optional[str] = Field(None, description="User agent string from the request")
    query_params: Optional[Dict[str, Any]] = Field(None, description="Query parameters for search actions as JSON")
    response_status: str = Field(
        ..., 
        pattern="^(success|denied|error)$",
        description="Response status: success, denied, or error"
    )

class AuditLogCreate(AuditLogBase):
    """Schema for creating a new audit log entry."""
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "action": "SEARCH",
                "document_id": None,
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
                "query_params": {
                    "query": "financial report Q4",
                    "department": "finance",
                    "top_k": 5,
                    "use_hybrid": True
                },
                "response_status": "success"
            }
        }

class AuditLogResponse(AuditLogBase):
    """Response schema for audit logs with metadata."""
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "456e7891-f23c-34e5-b567-537725285111",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "action": "SEARCH",
                "document_id": None,
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
                "query_params": {
                    "query": "financial report Q4",
                    "department": "finance",
                    "top_k": 5,
                    "use_hybrid": True
                },
                "response_status": "success",
                "created_at": "2024-01-01T10:30:00Z"
            }
        }
