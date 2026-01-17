from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime

class UserBase(BaseModel):
    """Base user schema with common fields."""
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    email: str = Field(..., description="User's email address")
    full_name: str = Field(..., min_length=1, max_length=100, description="User's full name")
    access_level: str = Field(
        ..., 
        pattern="^(low|medium|high|admin)$",
        description="Access level: low, medium, high, or admin"
    )
    department: str = Field(..., description="User's department/division")
    roles: List[str] = Field(default=[], description="User roles: admin, editor, viewer, etc.")

class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "email": "john@company.com",
                "full_name": "John Doe",
                "access_level": "medium",
                "department": "engineering",
                "roles": ["editor", "viewer"],
                "password": "secure_password_123"
            }
        }

class UserUpdate(BaseModel):
    """Schema for updating an existing user."""
    email: Optional[str] = Field(None, description="User's email address")
    full_name: Optional[str] = Field(None, min_length=1, max_length=100, description="User's full name")
    access_level: Optional[str] = Field(
        None,
        pattern="^(low|medium|high|admin)$",
        description="Access level: low, medium, high, or admin"
    )
    department: Optional[str] = Field(None, description="User's department/division")
    roles: Optional[List[str]] = Field(None, description="User roles: admin, editor, viewer, etc.")
    is_active: Optional[bool] = Field(None, description="Whether the user account is active")

class UserResponse(UserBase):
    """Response schema for users."""
    id: UUID
    is_active: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "username": "john_doe",
                "email": "john@company.com",
                "full_name": "John Doe",
                "access_level": "medium",
                "department": "engineering",
                "roles": ["editor", "viewer"],
                "is_active": True,
                "last_login": "2024-01-01T10:00:00Z",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }

class PermissionCheck(BaseModel):
    """Schema for checking user permissions."""
    document_id: UUID = Field(..., description="ID of the document to check access for")
    action: str = Field(
        ...,
        pattern="^(view|edit|delete|download)$",
        description="Action to check: view, edit, delete, or download"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "123e4567-e89b-12d3-a456-426614174000",
                "action": "view"
            }
        }
