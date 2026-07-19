"""
SQLAlchemy ORM Models

Database table definitions mapped to SQLAlchemy models.
These are infrastructure-level representations of domain entities.
Works with both PostgreSQL and SQLite.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import settings
from app.infrastructure.database import Base

# ── Type Helpers ────────────────────────────────────────


class StringUUID(TypeDecorator):
    """
    Platform-independent UUID type.

    PostgreSQL: uses native UUID type.
    SQLite: stores as String(36), auto-converts uuid.UUID ↔ str.
    """
    impl = String
    cache_ok = True

    def __init__(self):
        super().__init__(length=36)

    def load_dialect_impl(self, dialect: Dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import UUID as PG_UUID
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect: Dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        # SQLite: always convert to string
        return str(value)

    def process_result_value(self, value, dialect: Dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        # SQLite: convert stored string back to UUID for domain layer
        return uuid.UUID(value) if isinstance(value, str) else value


def UUIDType():
    """Return a platform-appropriate UUID column type."""
    return StringUUID()


def JSONType():
    """Return JSON column type. Uses generic JSON for SQLite, JSONB for PG."""
    if settings.DB_TYPE == "postgres":
        from sqlalchemy.dialects.postgresql import JSONB as _JSONB
        return _JSONB
    from sqlalchemy import JSON as _JSON
    return _JSON


def VectorType(dim: int = 384):
    """Return Vector column type, or Text fallback for SQLite."""
    if settings.DB_TYPE == "postgres":
        try:
            from pgvector.sqlalchemy import Vector as _Vector
            return _Vector(dim)
        except ImportError:
            return String(4096)
    return String(4096)


def now_default():
    """Return a compatible default timestamp."""
    if settings.DB_TYPE == "postgres":
        from sqlalchemy import text
        return text("NOW()")
    return func.now()


# ── Models ──────────────────────────────────────────────


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_default
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_default, onupdate=now_default
    )

    # Relationships
    conversations: Mapped[List["ConversationModel"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    memory_entries: Mapped[List["MemoryEntryModel"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    tasks: Mapped[List["ScheduledTaskModel"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class ConversationModel(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), default="New Conversation")
    model: Mapped[str] = mapped_column(String(50), default="gpt-4o")
    metadata_: Mapped[Dict[str, Any]] = mapped_column(JSONType(), default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_default
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_default, onupdate=now_default
    )

    # Relationships
    user: Mapped["UserModel"] = relationship(back_populates="conversations")
    messages: Mapped[List["MessageModel"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="MessageModel.created_at",
    )

    __table_args__ = (
        Index("idx_conversations_user_id", "user_id"),
    )


class MessageModel(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tool_calls: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONType(), nullable=True)
    tool_call_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_default
    )

    # Relationships
    conversation: Mapped["ConversationModel"] = relationship(back_populates="messages")

    __table_args__ = (
        Index("idx_messages_conversation_id", "conversation_id"),
        Index("idx_messages_created_at", "created_at"),
    )


class MemoryEntryModel(Base):
    __tablename__ = "memory_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[str]] = mapped_column(VectorType(384), nullable=True)
    memory_type: Mapped[str] = mapped_column(String(50), default="fact")
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    last_accessed: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    metadata_: Mapped[Dict[str, Any]] = mapped_column(JSONType(), default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_default
    )

    # Relationships
    user: Mapped["UserModel"] = relationship(back_populates="memory_entries")

    __table_args__ = (
        Index("idx_memory_user_id", "user_id"),
        Index("idx_memory_type", "memory_type"),
    )


class ScheduledTaskModel(Base):
    __tablename__ = "scheduled_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cron_expression: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    next_run: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_run: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    task_type: Mapped[str] = mapped_column(String(50), default="reminder")
    payload: Mapped[Dict[str, Any]] = mapped_column(JSONType(), default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_default
    )

    # Relationships
    user: Mapped["UserModel"] = relationship(back_populates="tasks")

    __table_args__ = (
        Index("idx_tasks_user_id", "user_id"),
        Index("idx_tasks_next_run", "next_run"),
    )


class PluginModel(Base):
    __tablename__ = "plugins"

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    entry_point: Mapped[str] = mapped_column(String(255), nullable=False)
    config_schema: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONType(), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_default
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_default, onupdate=now_default
    )
