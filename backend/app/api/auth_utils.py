"""
Authentication Utilities

JWT token extraction and user authentication middleware.
Provides the get_current_user dependency for protected routes.
"""

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.domain.entities import User
from app.application.services.auth_service import AuthService
from app.api.dependencies import get_auth_service

# Bearer token scheme
security_scheme = HTTPBearer(auto_error=False)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> Optional[User]:
    """
    Dependency that extracts the current user from the Authorization header.

    Returns None if no token is provided (for optional-auth endpoints).
    Raises 401 if token is invalid.
    """
    if not credentials:
        return None

    try:
        return await auth_service.get_current_user(credentials.credentials)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    """
    Dependency that requires authentication.

    Raises 401 if no valid token is provided.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return await auth_service.get_current_user(credentials.credentials)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
