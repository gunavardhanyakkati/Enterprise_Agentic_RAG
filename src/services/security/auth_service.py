import logging
from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import HTTPException, status
from jwt import PyJWTError

from src.config import get_settings
from src.schemas.common.security import TokenPayload, User

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service for JWT and LDAP integration."""

    def __init__(self):
        self.settings = get_settings()
        self.security_settings = self.settings.security
        self._jwt_secret = self.security_settings.jwt_secret
        self._jwt_algorithm = self.security_settings.jwt_algorithm
        self._jwt_expiry_hours = self.security_settings.jwt_expiry_hours
        self._ldap_configured = bool(self.security_settings.ldap_server)

    def create_access_token(self, user: User) -> str:
        """Create a JWT access token for a user.
        
        Args:
            user: The authenticated user
            
        Returns:
            JWT token string
        """
        expire = datetime.utcnow() + timedelta(hours=self._jwt_expiry_hours)
        
        payload = {
            "sub": user.id,
            "username": user.username,
            "email": user.email,
            "roles": user.roles,
            "access_levels": user.access_levels,
            "exp": int(expire.timestamp()),
        }
        
        token = jwt.encode(payload, self._jwt_secret, algorithm=self._jwt_algorithm)
        logger.info(f"Created access token for user: {user.username}")
        return token

    def verify_token(self, token: str) -> Optional[TokenPayload]:
        """Verify and decode a JWT token.
        
        Args:
            token: The JWT token to verify
            
        Returns:
            TokenPayload if valid, None if invalid
        """
        try:
            payload = jwt.decode(token, self._jwt_secret, algorithms=[self._jwt_algorithm])
            
            # Validate required fields
            required_fields = ["sub", "username", "email", "access_levels"]
            if not all(field in payload for field in required_fields):
                logger.warning(f"Token missing required fields: {payload}")
                return None
            
            return TokenPayload(
                sub=payload["sub"],
                username=payload["username"],
                email=payload["email"],
                roles=payload.get("roles", []),
                access_levels=payload["access_levels"],
                exp=payload["exp"],
            )
            
        except PyJWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error verifying token: {e}")
            return None

    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user via local or LDAP authentication.
        
        Args:
            username: Username/email to authenticate
            password: Plain text password
            
        Returns:
            User object if authenticated, None otherwise
        """
        logger.info(f"Attempting authentication for user: {username}")
        
        # TODO: Implement actual authentication logic
        # For now, this is a stub that returns a mock admin user
        # In production, this should:
        # 1. Check local database for user credentials
        # 2. If LDAP configured, attempt LDAP bind
        # 3. Verify password hash
        # 4. Return user object with permissions
        
        # Mock implementation for development
        if username == "admin" and password == "admin123":
            return User(
                id="admin-123",
                username="admin",
                email="admin@enterprise.com",
                full_name="System Administrator",
                department="IT",
                roles=["admin", "superuser"],
                access_levels=["public", "internal", "confidential", "restricted"],
                is_active=True,
                is_admin=True,
            )
        
        # Mock regular user
        if username == "user" and password == "user123":
            return User(
                id="user-456",
                username="user",
                email="user@enterprise.com",
                full_name="Regular User",
                department="Engineering",
                roles=["employee"],
                access_levels=["public", "internal"],
                is_active=True,
                is_admin=False,
            )
        
        logger.warning(f"Authentication failed for user: {username}")
        return None

    def get_current_user(self, token: str) -> User:
        """Get current user from JWT token (FastAPI dependency).
        
        Args:
            token: JWT token from Authorization header
            
        Returns:
            User object
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        token_payload = self.verify_token(token)
        
        if not token_payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if token is expired
        if datetime.utcnow().timestamp() > token_payload.exp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Convert TokenPayload back to User
        return User(
            id=token_payload.sub,
            username=token_payload.username,
            email=token_payload.email,
            full_name="",  # Not stored in token, would need DB lookup
            department="",  # Not stored in token
            roles=token_payload.roles,
            access_levels=token_payload.access_levels,
            is_active=True,
            is_admin="admin" in token_payload.roles or "superuser" in token_payload.roles,
        )
