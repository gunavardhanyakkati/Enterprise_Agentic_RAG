from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime

class PermissionBase(BaseModel):
    """Base permission schema."""
    name: str = Field(..., description="Unique name of the permission", min_length=1, max_length=100)
    description: str = Field(..., description="Description of what this permission allows", min_length=1, max_length=500)
    is_active: bool = Field(default=True, description="Whether this permission is currently active")

class PermissionCreate(PermissionBase):
    """Schema for creating a new permission."""
    class Config:
        json_schema_extra = {
            "example": {
                "name": "document:read",
                "description": "Allows reading/viewing documents",
                "is_active": True
            }
        }

class PermissionUpdate(BaseModel):
    """Schema for updating an existing permission."""
    name: Optional[str] = Field(None, description="Unique name of the permission", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="Description of what this permission allows", min_length=1, max_length=500)
    is_active: Optional[bool] = Field(None, description="Whether this permission is currently active")

class PermissionResponse(PermissionBase):
    """Response schema for permissions."""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "document:read",
                "description": "Allows reading/viewing documents",
                "is_active": True,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }
