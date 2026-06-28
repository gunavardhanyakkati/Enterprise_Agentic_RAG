from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AuditLogCreate(BaseModel):
    user_id: UUID
    action: str
    document_id: Optional[UUID] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    query_params: Optional[Dict[str, Any]] = None
    response_status: Optional[str] = None


class AuditLogResponse(BaseModel):
    id: UUID
    user_id: UUID
    action: str
    document_id: Optional[UUID] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    query_params: Optional[Dict[str, Any]] = None
    response_status: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
