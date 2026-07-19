"""
Repository Interfaces (Ports)

Abstract interface definitions following the Repository pattern.
These define WHAT the persistence layer must provide without
specifying HOW (framework-agnostic).
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from app.domain.entities import (
    Conversation,
    MemoryEntry,
    Message,
    ScheduledTask,
    User,
)


class IUserRepository(ABC):
    """Repository for User persistence operations."""

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        ...

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        ...

    @abstractmethod
    async def create(self, user: User) -> User:
        ...

    @abstractmethod
    async def update(self, user: User) -> User:
        ...

    @abstractmethod
    async def delete(self, user_id: UUID) -> None:
        ...


class IConversationRepository(ABC):
    """Repository for Conversation persistence operations."""

    @abstractmethod
    async def get_by_id(self, conversation_id: UUID) -> Optional[Conversation]:
        ...

    @abstractmethod
    async def list_by_user(
        self, user_id: UUID, limit: int = 50, offset: int = 0
    ) -> List[Conversation]:
        ...

    @abstractmethod
    async def create(self, conversation: Conversation) -> Conversation:
        ...

    @abstractmethod
    async def update(self, conversation: Conversation) -> Conversation:
        ...

    @abstractmethod
    async def delete(self, conversation_id: UUID) -> None:
        ...


class IMessageRepository(ABC):
    """Repository for Message persistence operations."""

    @abstractmethod
    async def get_by_conversation(
        self, conversation_id: UUID, limit: int = 100, before: Optional[UUID] = None
    ) -> List[Message]:
        ...

    @abstractmethod
    async def create(self, message: Message) -> Message:
        ...

    @abstractmethod
    async def create_batch(self, messages: List[Message]) -> List[Message]:
        ...


class IMemoryRepository(ABC):
    """Repository for MemoryEntry persistence with vector search."""

    @abstractmethod
    async def get_by_id(self, memory_id: UUID) -> Optional[MemoryEntry]:
        ...

    @abstractmethod
    async def search_similar(
        self,
        user_id: UUID,
        embedding: List[float],
        limit: int = 10,
        threshold: float = 0.7,
        memory_type: Optional[str] = None,
    ) -> List[MemoryEntry]:
        ...

    @abstractmethod
    async def create(self, memory: MemoryEntry) -> MemoryEntry:
        ...

    @abstractmethod
    async def update(self, memory: MemoryEntry) -> MemoryEntry:
        ...

    @abstractmethod
    async def delete(self, memory_id: UUID) -> None:
        ...

    @abstractmethod
    async def touch(self, memory_id: UUID) -> None:
        """Update access_count and last_accessed."""
        ...


class ITaskRepository(ABC):
    """Repository for ScheduledTask persistence operations."""

    @abstractmethod
    async def get_by_id(self, task_id: UUID) -> Optional[ScheduledTask]:
        ...

    @abstractmethod
    async def list_by_user(
        self, user_id: UUID, active_only: bool = True
    ) -> List[ScheduledTask]:
        ...

    @abstractmethod
    async def list_due(self, before: str, limit: int = 100) -> List[ScheduledTask]:
        ...

    @abstractmethod
    async def create(self, task: ScheduledTask) -> ScheduledTask:
        ...

    @abstractmethod
    async def update(self, task: ScheduledTask) -> ScheduledTask:
        ...

    @abstractmethod
    async def delete(self, task_id: UUID) -> None:
        ...
