"""
Authentication Routes

Handles user registration, login, and token refresh.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from app.domain.entities import User
from app.domain.exceptions import (
    InvalidCredentialsError,
    TokenExpiredError,
    TokenInvalidError,
    ValidationError,
)
from app.application.services.auth_service import AuthService
from app.api.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
    ErrorResponse,
)
from app.api.dependencies import get_auth_service
from app.api.auth_utils import get_current_user

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}},
)
async def register(
    request: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    """
    Register a new user account.

    Creates a new user with the provided email, password, and display name.
    Returns the created user profile (without tokens — use /login to get tokens).
    """
    try:
        user = await auth_service.register(
            email=request.email,
            password=request.password,
            display_name=request.display_name,
        )
        return UserResponse.model_validate(user)

    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={401: {"model": ErrorResponse}},
)
async def login(
    request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """
    Authenticate and return access/refresh tokens.

    The access token is short-lived (24h by default) and should be sent
    as a Bearer token in the Authorization header. The refresh token
    can be used to obtain new tokens without re-authenticating.
    """
    try:
        user, access_token, refresh_token = await auth_service.login(
            email=request.email,
            password=request.password,
        )
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    responses={401: {"model": ErrorResponse}},
)
async def refresh_token(
    request: RefreshRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """
    Obtain new access and refresh tokens using a refresh token.

    This allows the client to maintain a session without storing
    the user's password.
    """
    try:
        access_token, refresh_token = await auth_service.refresh_token(
            request.refresh_token
        )
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired. Please log in again.",
        )
    except TokenInvalidError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Get the currently authenticated user's profile.

    Requires a valid access token.
    """
    return UserResponse.model_validate(current_user)
