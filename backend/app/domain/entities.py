"""
Domain Entities

Core business objects that represent the fundamental concepts of Jarvis.
These are pure domain objects with no framework dependencies.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


# ── Value Objects ────────────────────────────────────────────


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class MemoryType(str, Enum):
    FACT = "fact"
    PREFERENCE = "preference"
    EVENT = "event"
    SKILL = "skill"
    SUMMARY = "summary"


class TaskType(str, Enum):
    REMINDER = "reminder"
    AUTOMATION = "automation"
    REPORT = "report"


@dataclass(frozen=True)
class UserId:
    """Strongly-typed user identifier."""
    value: UUID


@dataclass(frozen=True)
class ConversationId:
    """Strongly-typed conversation identifier."""
    value: UUID


# ── Entities ──────────────────────────────────────────────────


@dataclass
class User:
    """
    Represents a registered user of Jarvis.

    Attributes:
        id: Unique identifier.
        email: User's email address (unique, used for login).
        display_name: Human-readable name.
        password_hash: Bcrypt hash of the user's password.
        is_active: Whether the account is enabled.
        created_at: Account creation timestamp.
    """
    id: UUID
    email: str
    display_name: str
    password_hash: str
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def can_access(self) -> bool:
        """Check if the user is allowed to access the system."""
        return self.is_active


@dataclass
class Message:
    """
    A single message within a conversation.

    Attributes:
        id: Unique identifier.
        conversation_id: Parent conversation.
        role: Who sent the message (user, assistant, system, tool).
        content: The message text.
        tool_calls: OpenAI tool-call payload (if any).
        tool_call_id: ID linking to a prior assistant tool_call.
        token_count: Approximate token count of the message.
        created_at: When the message was sent.
    """
    id: UUID
    conversation_id: UUID
    role: MessageRole
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    token_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Conversation:
    """
    A conversation between a user and Jarvis.

    Attributes:
        id: Unique identifier.
        user_id: Owner of the conversation.
        title: Human-readable title (auto-generated or user-set).
        model: Which LLM model to use for this conversation.
        messages: Collection of messages in this conversation.
        metadata: Arbitrary key-value metadata.
        created_at: When the conversation started.
        updated_at: Last activity timestamp.
    """
    id: UUID
    user_id: UUID
    title: str = "New Conversation"
    model: str = "llama-3.1-8b-instant"
    messages: List[Message] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class MemoryEntry:
    """
    A piece of long-term memory stored with vector embedding.

    Attributes:
        id: Unique identifier.
        user_id: Owner of this memory.
        content: The memory text.
        embedding: Vector embedding (1536-dim for ada-002).
        memory_type: Classification of the memory.
        importance: Importance score (0.0 - 1.0).
        access_count: How many times this was retrieved.
        last_accessed: Last retrieval timestamp.
        metadata: Arbitrary key-value metadata.
        created_at: When the memory was created.
    """
    id: UUID
    user_id: UUID
    content: str
    embedding: Optional[List[float]] = None
    memory_type: MemoryType = MemoryType.FACT
    importance: float = 0.5
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ScheduledTask:
    """
    A scheduled task or reminder.

    Attributes:
        id: Unique identifier.
        user_id: Owner of the task.
        title: Short description.
        description: Detailed description.
        cron_expression: Cron schedule string.
        next_run: When the task will next execute.
        last_run: When the task last executed.
        is_active: Whether the task is enabled.
        task_type: Classification of the task.
        payload: Task-specific data.
        created_at: When the task was created.
    """
    id: UUID
    user_id: UUID
    title: str
    description: Optional[str] = None
    cron_expression: Optional[str] = None
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    is_active: bool = True
    task_type: TaskType = TaskType.REMINDER
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
