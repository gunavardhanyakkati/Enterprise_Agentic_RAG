from typing import List, Optional

from pydantic import BaseModel, Field


class AccessLevel:
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class User(BaseModel):
    """Schema for enterprise user information."""

    id: str = Field(..., description="Unique user identifier")
    username: str = Field(..., description="Username for login")
    email: str = Field(..., description="User email address")
    full_name: str = Field(..., description="User's full name")
    department: str = Field(..., description="User's department")
    roles: List[str] = Field(default_factory=list, description="User's assigned roles")
    access_levels: List[str] = Field(
        default_factory=lambda: [AccessLevel.PUBLIC, AccessLevel.INTERNAL],
        description="Document access levels user can view"
    )
    is_active: bool = Field(default=True, description="Whether user account is active")
    is_admin: bool = Field(default=False, description="Whether user has admin privileges")


class Permission(BaseModel):
    """Schema for RBAC permission."""

    resource: str = Field(..., description="Resource name (e.g., 'document', 'audit_log')")
    action: str = Field(..., description="Action (e.g., 'read', 'write', 'delete')")
    access_level: str = Field(..., description="Required access level for this permission")


class TokenPayload(BaseModel):
    """Schema for JWT token payload."""

    sub: str = Field(..., description="Subject (user ID)")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="User email")
    roles: List[str] = Field(default_factory=list, description="User roles")
    access_levels: List[str] = Field(..., description="User access levels")
    exp: int = Field(..., description="Expiration timestamp")


class LoginRequest(BaseModel):
    """Schema for login request."""

    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class LoginResponse(BaseModel):
    """Schema for login response."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiry in seconds")
    user: User = Field(..., description="User information")
