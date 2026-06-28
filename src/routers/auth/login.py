import logging
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from src.dependencies import AuthDep, AuditLoggerDep, UserDep
from src.schemas.common.security import LoginRequest, LoginResponse, User
from src.services.security.auth_service import AuthService
from src.services.security.audit_logger import AuditLogger

logger = logging.getLogger(__name__)

router = APIRouter(tags=["authentication"])


@router.post("/login", response_model=LoginResponse)
async def login(
    auth_service: AuthDep,
    audit_logger: AuditLoggerDep,
    form_data: OAuth2PasswordRequestForm = Depends(),
    ip_address: Optional[str] = None,
):
    """Authenticate user and return JWT access token.
    
    This endpoint authenticates a user via username/password and returns
    a JWT token for subsequent API requests. All authentication attempts
    are logged for audit compliance.
    
    Args:
        form_data: OAuth2 password request form with username and password
        auth_service: Authentication service for user verification
        audit_logger: Audit logger for security event tracking
        ip_address: Client IP address (auto-detected if not provided)
        
    Returns:
        LoginResponse with access token, token type, and user information
        
    Raises:
        HTTPException: 
            - 401 if authentication fails
            - 500 if token generation fails
    """
    logger.info(f"Login attempt for user: {form_data.username}")
    
    # Attempt authentication
    user = await auth_service.authenticate_user(form_data.username, form_data.password)
    
    if not user:
        # Log failed login attempt
        audit_logger.log_user_login(
            user=User(
                id="unknown",
                username=form_data.username,
                email="",
                full_name="",
                department="",
                roles=[],
                access_levels=[],
                is_active=False,
                is_admin=False,
            ),
            success=False,
            ip_address=ip_address,
        )
        
        logger.warning(f"Authentication failed for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate access token
    try:
        access_token = auth_service.create_access_token(user)
        logger.info(f"Token generated successfully for user: {user.username}")
    except Exception as e:
        logger.error(f"Token generation failed for user {form_data.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate access token",
        )
    
    # Log successful login
    audit_logger.log_user_login(
        user=user,
        success=True,
        ip_address=ip_address,
    )
    
    # Create login response
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=auth_service.settings.security.jwt_expiry_hours * 3600,
        user=user,
    )


@router.post("/login/json", response_model=LoginResponse)
async def login_json(
    login_request: LoginRequest,
    auth_service: AuthDep,
    audit_logger: AuditLoggerDep,
    ip_address: Optional[str] = None,
):
    """Alternative login endpoint that accepts JSON payload instead of form data.
    
    This endpoint provides the same functionality as /login but accepts
    a JSON body, which can be more convenient for some client applications.
    
    Args:
        login_request: Login request with username and password
        auth_service: Authentication service
        audit_logger: Audit logger
        ip_address: Client IP address
        
    Returns:
        LoginResponse with access token and user info
        
    Raises:
        HTTPException: If authentication fails
    """
    logger.info(f"JSON login attempt for user: {login_request.username}")
    
    # Attempt authentication
    user = await auth_service.authenticate_user(login_request.username, login_request.password)
    
    if not user:
        # Log failed login attempt
        audit_logger.log_user_login(
            user=User(
                id="unknown",
                username=login_request.username,
                email="",
                full_name="",
                department="",
                roles=[],
                access_levels=[],
                is_active=False,
                is_admin=False,
            ),
            success=False,
            ip_address=ip_address,
        )
        
        logger.warning(f"Authentication failed for user: {login_request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate access token
    try:
        access_token = auth_service.create_access_token(user)
        logger.info(f"Token generated successfully for user: {user.username}")
    except Exception as e:
        logger.error(f"Token generation failed for user {login_request.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate access token",
        )
    
    # Log successful login
    audit_logger.log_user_login(
        user=user,
        success=True,
        ip_address=ip_address,
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=auth_service.settings.security.jwt_expiry_hours * 3600,
        user=user,
    )


@router.get("/me", response_model=User)
async def get_current_user_info(
    user: UserDep,
):
    """Get information about the currently authenticated user.
    
    Args:
        user: The authenticated user from the JWT token
        
    Returns:
        User object with profile information
    """
    logger.debug(f"Fetching user info for: {user.username}")
    return user


@router.post("/logout")
async def logout(
    user: UserDep,
    audit_logger: AuditLoggerDep,
):
    """Logout endpoint for audit logging purposes.
    
    Note: Since JWT tokens are stateless, this endpoint doesn't invalidate the token.
    It's primarily for audit logging and client-side token cleanup.
    
    Args:
        user: The authenticated user
        audit_logger: Audit logger
        
    Returns:
        Success message
    """
    logger.info(f"Logout requested by user: {user.username}")
    
    # Log the logout event
    audit_logger.log_security_event(
        user=user,
        event="user_logout",
        reason="User initiated logout",
        severity="low",
    )
    
    return {"message": "Logout successful. Please clear your JWT token on the client side."}
