"""
Unit Tests — Authentication Service

Tests for user registration, login, token management, and validation.
"""

import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock

from app.domain.entities import User
from app.domain.exceptions import (
    InvalidCredentialsError,
    ValidationError,
    TokenExpiredError,
    TokenInvalidError,
)
from app.application.services.auth_service import AuthService


class TestPasswordUtilities:
    """Tests for password hashing and verification."""

    def test_hash_password_returns_different_hash(self):
        """Hashing the same password twice produces different hashes (salt)."""
        hash1 = AuthService.hash_password("TestPass123")
        hash2 = AuthService.hash_password("TestPass123")
        assert hash1 != hash2
        assert hash1.startswith("$2b$")  # bcrypt prefix

    def test_verify_password_correct(self):
        """Correct password passes verification."""
        plain = "SecureP@ss1"
        hashed = AuthService.hash_password(plain)
        assert AuthService.verify_password(plain, hashed) is True

    def test_verify_password_incorrect(self):
        """Incorrect password fails verification."""
        hashed = AuthService.hash_password("SecureP@ss1")
        assert AuthService.verify_password("WrongPassword", hashed) is False


class TestValidation:
    """Tests for input validation."""

    def test_validate_password_too_short(self):
        with pytest.raises(ValidationError, match="8 characters"):
            AuthService._validate_password_strength("Ab1")

    def test_validate_password_no_uppercase(self):
        with pytest.raises(ValidationError, match="uppercase"):
            AuthService._validate_password_strength("alllowercase1")

    def test_validate_password_no_lowercase(self):
        with pytest.raises(ValidationError, match="lowercase"):
            AuthService._validate_password_strength("ALLUPPERCASE1")

    def test_validate_password_no_digit(self):
        with pytest.raises(ValidationError, match="digit"):
            AuthService._validate_password_strength("NoDigitsHere")

    def test_validate_password_valid(self):
        # Should not raise
        AuthService._validate_password_strength("ValidP@ss1")

    def test_validate_email_invalid(self):
        with pytest.raises(ValidationError, match="Invalid email"):
            AuthService._validate_email("not-an-email")

    def test_validate_email_too_long(self):
        long_email = "a" * 256 + "@test.com"
        with pytest.raises(ValidationError):
            AuthService._validate_email(long_email)


class TestTokenUtilities:
    """Tests for JWT token creation and decoding."""

    async def test_create_and_decode_access_token(self, auth_service):
        user_id = uuid.uuid4()
        token = auth_service._create_access_token(user_id)

        payload = auth_service._decode_token(token, expected_type="access")
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"
        assert "exp" in payload

    async def test_decode_wrong_token_type(self, auth_service):
        user_id = uuid.uuid4()
        access_token = auth_service._create_access_token(user_id)

        with pytest.raises(TokenInvalidError):
            auth_service._decode_token(access_token, expected_type="refresh")

    async def test_decode_invalid_token(self, auth_service):
        with pytest.raises(TokenInvalidError):
            auth_service._decode_token("not.a.valid.token")


class TestRegistration:
    """Tests for user registration."""

    async def test_register_success(self, auth_service):
        user = await auth_service.register(
            email="test@example.com",
            password="ValidP@ss1",
            display_name="Test User",
        )

        assert user.email == "test@example.com"
        assert user.display_name == "Test User"
        assert user.is_active is True
        assert user.password_hash != "ValidP@ss1"  # Should be hashed

    async def test_register_duplicate_email(self, auth_service):
        await auth_service.register(
            email="dupe@example.com",
            password="ValidP@ss1",
            display_name="First User",
        )

        with pytest.raises(ValidationError, match="already registered"):
            await auth_service.register(
                email="dupe@example.com",
                password="ValidP@ss1",
                display_name="Second User",
            )

    async def test_register_empty_display_name(self, auth_service):
        with pytest.raises(ValidationError, match="2 characters"):
            await auth_service.register(
                email="test@example.com",
                password="ValidP@ss1",
                display_name="A",
            )

    async def test_register_normalizes_email(self, auth_service):
        user = await auth_service.register(
            email="  TEST@Example.COM  ",
            password="ValidP@ss1",
            display_name="Test User",
        )
        assert user.email == "test@example.com"


class TestLogin:
    """Tests for user login."""

    async def test_login_success(self, auth_service):
        # Register first
        await auth_service.register(
            email="login@example.com",
            password="ValidP@ss1",
            display_name="Login User",
        )

        # Login
        user, access_token, refresh_token = await auth_service.login(
            email="login@example.com",
            password="ValidP@ss1",
        )

        assert user.email == "login@example.com"
        assert access_token is not None
        assert refresh_token is not None

    async def test_login_wrong_password(self, auth_service):
        await auth_service.register(
            email="login2@example.com",
            password="ValidP@ss1",
            display_name="Login User",
        )

        with pytest.raises(InvalidCredentialsError):
            await auth_service.login(
                email="login2@example.com",
                password="WrongPassword",
            )

    async def test_login_nonexistent_user(self, auth_service):
        with pytest.raises(InvalidCredentialsError):
            await auth_service.login(
                email="noone@example.com",
                password="AnyPass1",
            )

    async def test_login_case_insensitive_email(self, auth_service):
        await auth_service.register(
            email="case@example.com",
            password="ValidP@ss1",
            display_name="Case User",
        )

        user, _, _ = await auth_service.login(
            email="CASE@EXAMPLE.COM",
            password="ValidP@ss1",
        )

        assert user.email == "case@example.com"


class TestTokenRefresh:
    """Tests for token refresh flow."""

    async def test_refresh_token_success(self, auth_service):
        await auth_service.register(
            email="refresh@example.com",
            password="ValidP@ss1",
            display_name="Refresh User",
        )

        _, _, refresh_token = await auth_service.login(
            email="refresh@example.com",
            password="ValidP@ss1",
        )

        new_access, new_refresh = await auth_service.refresh_token(refresh_token)

        assert new_access is not None
        assert new_refresh is not None
        assert new_access != refresh_token

    async def test_refresh_with_access_token_fails(self, auth_service):
        await auth_service.register(
            email="wrongtype@example.com",
            password="ValidP@ss1",
            display_name="Wrong Type",
        )

        _, access_token, _ = await auth_service.login(
            email="wrongtype@example.com",
            password="ValidP@ss1",
        )

        with pytest.raises(TokenInvalidError):
            await auth_service.refresh_token(access_token)
