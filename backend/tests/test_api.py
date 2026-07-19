"""
Unit Tests — API Endpoints

Integration-style tests for the FastAPI routes using HTTPX.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.domain.entities import User


@pytest.fixture
def test_app():
    """Provide the FastAPI test application."""
    return app


@pytest.mark.asyncio
class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    async def test_health_check(self, test_app):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "jarvis"


@pytest.mark.asyncio
class TestAuthEndpoints:
    """Tests for authentication endpoints."""

    async def test_register_success(self, test_app):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "newuser@test.com",
                    "password": "ValidP@ss1",
                    "display_name": "New User",
                },
            )
            assert response.status_code == 201
            data = response.json()
            assert data["email"] == "newuser@test.com"
            assert data["display_name"] == "New User"
            assert "password" not in data

    async def test_register_weak_password(self, test_app):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "weak@test.com",
                    "password": "short",
                    "display_name": "Weak Pass",
                },
            )
            assert response.status_code == 400

    async def test_login_flow(self, test_app):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Register
            await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "login-test@test.com",
                    "password": "ValidP@ss1",
                    "display_name": "Login Test",
                },
            )

            # Login
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": "login-test@test.com", "password": "ValidP@ss1"},
            )
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "bearer"

    async def test_login_invalid_credentials(self, test_app):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": "noone@test.com", "password": "WrongPass1"},
            )
            assert response.status_code == 401

    async def test_get_me_requires_auth(self, test_app):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/auth/me")
            assert response.status_code == 401

    async def test_get_me_with_valid_token(self, test_app):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Register + Login
            await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "me-test@test.com",
                    "password": "ValidP@ss1",
                    "display_name": "Me Test",
                },
            )
            login_resp = await client.post(
                "/api/v1/auth/login",
                json={"email": "me-test@test.com", "password": "ValidP@ss1"},
            )
            token = login_resp.json()["access_token"]

            # Get me
            response = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["email"] == "me-test@test.com"


@pytest.mark.asyncio
class TestChatEndpoints:
    """Tests for chat endpoints."""

    async def test_list_conversations_empty(self, test_app):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Register + Login
            await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "chat-test@test.com",
                    "password": "ValidP@ss1",
                    "display_name": "Chat Test",
                },
            )
            login_resp = await client.post(
                "/api/v1/auth/login",
                json={"email": "chat-test@test.com", "password": "ValidP@ss1"},
            )
            token = login_resp.json()["access_token"]

            response = await client.get(
                "/api/v1/chat/conversations",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            assert response.json() == []
