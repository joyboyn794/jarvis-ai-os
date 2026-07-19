"""
Authentication Service

Handles user registration, login, token management, and
credential validation. Uses bcrypt for password hashing
and JWT for token-based authentication.
"""

import uuid
from datetime import datetime, timedelta, timezone

import structlog
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings
from app.domain.entities import User
from app.domain.exceptions import (
    InvalidCredentialsError,
    TokenExpiredError,
    TokenInvalidError,
    UserNotFoundError,
    ValidationError,
)
from app.domain.repositories import IUserRepository
from app.application.interfaces import IAuthService

logger = structlog.get_logger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService(IAuthService):
    """
    Authentication service implementing JWT-based auth with bcrypt passwords.

    Token types:
    - access_token: Short-lived (default 24h), used for API authorization.
    - refresh_token: Long-lived (default 30d), used to obtain new access tokens.
    """

    def __init__(self, user_repo: IUserRepository):
        self.user_repo = user_repo

    # ── Password Utilities ──────────────────────────────────

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a plain-text password using bcrypt."""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plain-text password against its bcrypt hash."""
        return pwd_context.verify(plain_password, hashed_password)

    # ── Token Utilities ─────────────────────────────────────

    def _create_access_token(self, user_id: uuid.UUID) -> str:
        """Create a short-lived access JWT token."""
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_EXPIRE_MINUTES
        )
        payload = {
            "sub": str(user_id),
            "type": "access",
            "iat": datetime.now(timezone.utc),
            "exp": expire,
        }
        return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    def _create_refresh_token(self, user_id: uuid.UUID) -> str:
        """Create a long-lived refresh JWT token."""
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        payload = {
            "sub": str(user_id),
            "type": "refresh",
            "iat": datetime.now(timezone.utc),
            "exp": expire,
        }
        return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    def _decode_token(self, token: str, expected_type: str = "access") -> dict:
        """
        Decode and validate a JWT token.

        Args:
            token: The JWT token string.
            expected_type: Expected token type ('access' or 'refresh').

        Returns:
            Decoded token payload.

        Raises:
            TokenExpiredError: Token has expired.
            TokenInvalidError: Token is invalid or wrong type.
        """
        try:
            payload = jwt.decode(
                token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
            )
            if payload.get("type") != expected_type:
                raise TokenInvalidError()
            return payload
        except JWTError as e:
            if "expired" in str(e).lower():
                raise TokenExpiredError()
            raise TokenInvalidError() from e

    # ── Validation ──────────────────────────────────────────

    @staticmethod
    def _validate_password_strength(password: str) -> None:
        """Validate password meets minimum requirements."""
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters", field="password")
        if not any(c.isupper() for c in password):
            raise ValidationError(
                "Password must contain at least one uppercase letter", field="password"
            )
        if not any(c.islower() for c in password):
            raise ValidationError(
                "Password must contain at least one lowercase letter", field="password"
            )
        if not any(c.isdigit() for c in password):
            raise ValidationError(
                "Password must contain at least one digit", field="password"
            )

    @staticmethod
    def _validate_email(email: str) -> None:
        """Basic email format validation."""
        if "@" not in email or "." not in email.split("@")[-1]:
            raise ValidationError("Invalid email format", field="email")
        if len(email) > 255:
            raise ValidationError("Email must be 255 characters or fewer", field="email")

    # ── Public Methods ──────────────────────────────────────

    async def register(self, email: str, password: str, display_name: str) -> User:
        """
        Register a new user account.

        Validates input, checks for duplicate email, hashes password,
        and persists the new user.

        Raises:
            ValidationError: If email/password/name is invalid.
            ValidationError: If email is already registered.
        """
        self._validate_email(email)
        self._validate_password_strength(password)

        if not display_name or len(display_name.strip()) < 2:
            raise ValidationError(
                "Display name must be at least 2 characters", field="display_name"
            )

        # Check for duplicate email
        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise ValidationError("Email is already registered", field="email")

        # Create user
        user = User(
            id=uuid.uuid4(),
            email=email.lower().strip(),
            display_name=display_name.strip(),
            password_hash=self.hash_password(password),
        )

        created_user = await self.user_repo.create(user)
        logger.info("User registered", user_id=str(created_user.id))
        return created_user

    async def login(self, email: str, password: str) -> tuple[User, str, str]:
        """
        Authenticate a user and return tokens.

        Args:
            email: User's email address.
            password: User's plain-text password.

        Returns:
            Tuple of (User, access_token, refresh_token).

        Raises:
            InvalidCredentialsError: If email or password is wrong.
        """
        user = await self.user_repo.get_by_email(email.lower().strip())
        if not user:
            raise InvalidCredentialsError()

        if not self.verify_password(password, user.password_hash):
            raise InvalidCredentialsError()

        if not user.is_active:
            raise InvalidCredentialsError()

        access_token = self._create_access_token(user.id)
        refresh_token = self._create_refresh_token(user.id)

        logger.info("User logged in", user_id=str(user.id))
        return user, access_token, refresh_token

    async def refresh_token(self, refresh_token: str) -> tuple[str, str]:
        """
        Obtain new tokens using a refresh token.

        Args:
            refresh_token: A valid refresh token.

        Returns:
            Tuple of (new_access_token, new_refresh_token).

        Raises:
            TokenExpiredError: Refresh token has expired.
            TokenInvalidError: Token is invalid.
        """
        payload = self._decode_token(refresh_token, expected_type="refresh")
        user_id = uuid.UUID(payload["sub"])

        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise TokenInvalidError()

        new_access = self._create_access_token(user_id)
        new_refresh = self._create_refresh_token(user_id)

        logger.info("Token refreshed", user_id=str(user_id))
        return new_access, new_refresh

    async def get_current_user(self, token: str) -> User:
        """
        Validate an access token and return the corresponding user.

        Args:
            token: Access token string.

        Returns:
            The authenticated User.

        Raises:
            TokenExpiredError: Token has expired.
            TokenInvalidError: Token is invalid.
            UserNotFoundError: User no longer exists.
        """
        payload = self._decode_token(token, expected_type="access")
        user_id = uuid.UUID(payload["sub"])

        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(str(user_id))

        return user
