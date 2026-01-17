from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime

class PolicyBase(BaseModel):
    """Base policy schema."""
    name: str = Field(..., description="Unique name of the policy", min_length=1, max_length=100)
    description: str = Field(..., description="Description of what this policy does", min_length=1, max_length=500)
    policy_type: str = Field(..., description="Type of policy: retention, access, security, etc.", min_length=1, max_length=50)
    config: Dict[str, Any] = Field(default_factory=dict, description="Policy-specific configuration as JSON")
    is_active: bool = Field(default=True, description="Whether this policy is currently active")

class PolicyCreate(PolicyBase):
    """Schema for creating a new policy."""
    class Config:
        json_schema_extra = {
            "example": {
                "name": "retention_policy",
                "description": "Automatically archives documents older than 1 year",
                "policy_type": "retention",
                "config": {
                    "retention_days": 365,
                    "archive_location": "/archive"
                },
                "is_active": True
            }
        }

class PolicyUpdate(BaseModel):
    """Schema for updating an existing policy."""
    name: Optional[str] = Field(None, description="Unique name of the policy", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="Description of what this policy does", min_length=1, max_length=500)
    policy_type: Optional[str] = Field(None, description="Type of policy: retention, access, security, etc.", min_length=1, max_length=50)
    config: Optional[Dict[str, Any]] = Field(None, description="Policy-specific configuration as JSON")
    is_active: Optional[bool] = Field(None, description="Whether this policy is currently active")

class PolicyResponse(PolicyBase):
    """Response schema for policies."""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "retention_policy",
                "description": "Automatically archives documents older than 1 year",
                "policy_type": "retention",
                "config": {
                    "retention_days": 365,
                    "archive_location": "/archive"
                },
                "is_active": True,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }
