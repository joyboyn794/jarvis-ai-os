"""
Pydantic Schemas (DTOs)

Request/Response models for the API layer.
These are separate from domain entities to maintain
clean architecture boundaries.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Authentication ──────────────────────────────────────────


class RegisterRequest(BaseModel):
    """Request body for user registration."""
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str = Field(..., min_length=2, max_length=100)


class LoginRequest(BaseModel):
    """Request body for user login."""
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


class TokenResponse(BaseModel):
    """Response containing access and refresh tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Request body for token refresh."""
    refresh_token: str


class UserResponse(BaseModel):
    """Public user profile."""
    id: UUID
    email: str
    display_name: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Chat ────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    """Request body for sending a chat message."""
    conversation_id: Optional[UUID] = None
    message: str = Field(..., min_length=1, max_length=10000)
    model: str = "llama-3.1-8b-instant"
    stream: bool = True
    use_memory: bool = True


class MessageResponse(BaseModel):
    """Response representing a single message."""
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    token_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    """Response representing a conversation."""
    id: UUID
    title: str
    model: str
    message_count: int = 0
    last_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetailResponse(BaseModel):
    """Response with conversation and all messages."""
    id: UUID
    title: str
    model: str
    messages: List[MessageResponse]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Memory ──────────────────────────────────────────────────


class MemorySearchRequest(BaseModel):
    """Request body for searching memories."""
    query: str = Field(..., min_length=1, max_length=1000)
    limit: int = Field(default=10, ge=1, le=50)
    memory_type: Optional[str] = None


class MemoryEntryResponse(BaseModel):
    """Response representing a memory entry."""
    id: UUID
    content: str
    memory_type: str
    importance: float
    access_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class MemorySearchResultResponse(BaseModel):
    """Response representing a memory search result."""
    entry: MemoryEntryResponse
    similarity: float


# ── Tasks ───────────────────────────────────────────────────


class CreateTaskRequest(BaseModel):
    """Request body for creating a scheduled task."""
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="", max_length=5000)
    cron_expression: str = Field(..., min_length=1, max_length=100)


class TaskResponse(BaseModel):
    """Response representing a scheduled task."""
    id: UUID
    title: str
    description: Optional[str]
    cron_expression: Optional[str]
    next_run: Optional[datetime]
    last_run: Optional[datetime]
    is_active: bool
    task_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Common ──────────────────────────────────────────────────


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str
    type: str = "error"
    code: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str
