from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class LoginRequest(BaseModel):
    """Schema for user login requests."""
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=8, description="Password")

    class Config:
        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "password": "secure_password_123"
            }
        }


class LoginResponse(BaseModel):
    """Schema for login responses with JWT token."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type (always 'bearer')")
    expires_in: int = Field(..., description="Token expiry time in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiw...",
                "token_type": "bearer",
                "expires_in": 86400
            }
        }


class TokenPayload(BaseModel):
    """Schema for JWT token payload (decoded)."""
    sub: str = Field(..., description="User ID (UUID)")
    username: str = Field(..., description="Username")
    access_level: str = Field(..., description="User's access level: low/medium/high/admin")
    department: str = Field(..., description="User's department/division")
    roles: List[str] = Field(..., description="User's roles: admin, editor, viewer, etc.")
    exp: int = Field(..., description="Expiration timestamp (Unix epoch)")

    class Config:
        json_schema_extra = {
            "example": {
                "sub": "123e4567-e89b-12d3-a456-426614174000",
                "username": "john_doe",
                "access_level": "medium",
                "department": "engineering",
                "roles": ["editor", "viewer"],
                "exp": 1704067200
            }
        }


class RefreshTokenRequest(BaseModel):
    """Schema for token refresh requests."""
    refresh_token: str = Field(..., description="Refresh token")

    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiw..."
            }
        }


class ForgotPasswordRequest(BaseModel):
    """Schema for forgot password requests."""
    email: str = Field(..., description="User's email address")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "john@company.com"
            }
        }


class ResetPasswordRequest(BaseModel):
    """Schema for password reset requests."""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New password")

    class Config:
        json_schema_extra = {
            "example": {
                "token": "reset-token-12345",
                "new_password": "new_secure_password_123"
            }
        }
