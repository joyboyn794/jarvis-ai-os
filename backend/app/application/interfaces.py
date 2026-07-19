"""
Application Service Interfaces

These interfaces define the contract for application services
that orchestrate domain logic across multiple repositories and
external services.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator, List, Optional
from uuid import UUID

from app.domain.entities import (
    Conversation,
    MemoryEntry,
    Message,
    ScheduledTask,
    User,
)


# ── DTOs ────────────────────────────────────────────────────


@dataclass
class ChatRequest:
    """Incoming chat message request."""
    conversation_id: Optional[UUID] = None
    message: str = ""
    model: str = "gpt-4o"
    stream: bool = True
    use_memory: bool = True


@dataclass
class ChatResponse:
    """Chat response with streaming or complete content."""
    conversation_id: UUID
    message_id: UUID
    content: str
    is_complete: bool = False
    tool_calls: Optional[List[dict]] = None
    tokens_used: int = 0


@dataclass
class MemorySearchResult:
    """Result from a memory search."""
    entry: MemoryEntry
    similarity: float


# ── Service Interfaces ──────────────────────────────────────


class IAuthService(ABC):
    """Service for authentication and authorization."""

    @abstractmethod
    async def register(self, email: str, password: str, display_name: str) -> User:
        ...

    @abstractmethod
    async def login(self, email: str, password: str) -> tuple[User, str, str]:
        """Returns (user, access_token, refresh_token)."""
        ...

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> tuple[str, str]:
        """Returns (new_access_token, new_refresh_token)."""
        ...

    @abstractmethod
    async def get_current_user(self, token: str) -> User:
        ...


class IChatService(ABC):
    """Service for chat functionality including LLM interaction."""

    @abstractmethod
    async def send_message(self, user_id: UUID, request: ChatRequest) -> ChatResponse:
        """Send a message and get a complete response."""
        ...

    @abstractmethod
    async def stream_message(
        self, user_id: UUID, request: ChatRequest
    ) -> AsyncIterator[ChatResponse]:
        """Send a message and stream the response."""
        ...

    @abstractmethod
    async def get_conversation(self, conversation_id: UUID, user_id: UUID) -> Conversation:
        ...

    @abstractmethod
    async def list_conversations(
        self, user_id: UUID, limit: int = 50, offset: int = 0
    ) -> List[Conversation]:
        ...

    @abstractmethod
    async def delete_conversation(self, conversation_id: UUID, user_id: UUID) -> None:
        ...


class IMemoryService(ABC):
    """Service for long-term memory operations."""

    @abstractmethod
    async def store(self, user_id: UUID, content: str, memory_type: str = "fact") -> MemoryEntry:
        ...

    @abstractmethod
    async def search(
        self, user_id: UUID, query: str, limit: int = 10, memory_type: Optional[str] = None
    ) -> List[MemorySearchResult]:
        ...

    @abstractmethod
    async def retrieve_context(
        self, user_id: UUID, query: str, limit: int = 5
    ) -> str:
        """Get formatted memory context for inclusion in prompts."""
        ...

    @abstractmethod
    async def consolidate(self, user_id: UUID) -> None:
        """Consolidate recent conversations into summary memories."""
        ...


class ITaskService(ABC):
    """Service for scheduled tasks and reminders."""

    @abstractmethod
    async def create_task(
        self, user_id: UUID, title: str, description: str, cron: str
    ) -> ScheduledTask:
        ...

    @abstractmethod
    async def list_tasks(self, user_id: UUID) -> List[ScheduledTask]:
        ...

    @abstractmethod
    async def delete_task(self, task_id: UUID, user_id: UUID) -> None:
        ...
