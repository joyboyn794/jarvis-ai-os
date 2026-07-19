"""
Unit Tests — Domain Entities

Tests for entity creation, immutability (where applicable),
and domain behavior.
"""

import uuid
from datetime import datetime

from app.domain.entities import (
    User,
    Conversation,
    Message,
    MessageRole,
    MemoryEntry,
    MemoryType,
    ScheduledTask,
    TaskType,
)
from app.domain.exceptions import (
    JarvisDomainError,
    AuthenticationError,
    InvalidCredentialsError,
    NotFoundError,
    ValidationError,
    TokenLimitExceededError,
)


class TestUserEntity:
    """Tests for the User domain entity."""

    def test_user_creation(self):
        user = User(
            id=uuid.uuid4(),
            email="tony@starkindustries.com",
            display_name="Tony Stark",
            password_hash="hashed_password",
        )
        assert user.email == "tony@starkindustries.com"
        assert user.is_active is True
        assert isinstance(user.created_at, datetime)

    def test_user_can_access_when_active(self):
        user = User(
            id=uuid.uuid4(),
            email="active@user.com",
            display_name="Active",
            password_hash="hash",
            is_active=True,
        )
        assert user.can_access() is True

    def test_user_cannot_access_when_inactive(self):
        user = User(
            id=uuid.uuid4(),
            email="inactive@user.com",
            display_name="Inactive",
            password_hash="hash",
            is_active=False,
        )
        assert user.can_access() is False


class TestMessageEntity:
    """Tests for the Message domain entity."""

    def test_message_creation(self):
        msg = Message(
            id=uuid.uuid4(),
            conversation_id=uuid.uuid4(),
            role=MessageRole.USER,
            content="Hello, Jarvis.",
        )
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello, Jarvis."
        assert msg.token_count == 0

    def test_message_roles(self):
        for role in MessageRole:
            msg = Message(
                id=uuid.uuid4(),
                conversation_id=uuid.uuid4(),
                role=role,
                content="test",
            )
            assert msg.role == role


class TestConversationEntity:
    """Tests for the Conversation domain entity."""

    def test_conversation_creation(self):
        conv = Conversation(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            title="Project Discussion",
        )
        assert conv.title == "Project Discussion"
        assert conv.model == "gpt-4o"
        assert len(conv.messages) == 0

    def test_conversation_with_messages(self):
        conv = Conversation(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        )
        msg1 = Message(
            id=uuid.uuid4(),
            conversation_id=conv.id,
            role=MessageRole.USER,
            content="Hello",
        )
        msg2 = Message(
            id=uuid.uuid4(),
            conversation_id=conv.id,
            role=MessageRole.ASSISTANT,
            content="Hello, sir.",
        )
        conv.messages = [msg1, msg2]
        assert len(conv.messages) == 2


class TestMemoryEntryEntity:
    """Tests for the MemoryEntry domain entity."""

    def test_memory_entry_creation(self):
        entry = MemoryEntry(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            content="User prefers dark mode",
            memory_type=MemoryType.PREFERENCE,
            importance=0.8,
        )
        assert entry.memory_type == MemoryType.PREFERENCE
        assert entry.importance == 0.8
        assert entry.access_count == 0
        assert entry.embedding is None


class TestScheduledTaskEntity:
    """Tests for the ScheduledTask domain entity."""

    def test_task_creation(self):
        task = ScheduledTask(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            title="Standup Meeting",
            cron_expression="0 9 * * 1-5",
            task_type=TaskType.REMINDER,
        )
        assert task.title == "Standup Meeting"
        assert task.is_active is True
        assert task.task_type == TaskType.REMINDER


class TestDomainExceptions:
    """Tests for the exception hierarchy."""

    def test_jarvis_domain_error(self):
        error = JarvisDomainError("Something went wrong")
        assert error.code == "DOMAIN_ERROR"
        assert str(error) == "Something went wrong"

    def test_invalid_credentials(self):
        error = InvalidCredentialsError()
        assert error.code == "INVALID_CREDENTIALS"

    def test_not_found_error(self):
        error = NotFoundError("User", "abc-123")
        assert "User" in str(error)
        assert "abc-123" in str(error)
        assert error.code == "NOT_FOUND"

    def test_validation_error_with_field(self):
        error = ValidationError("Invalid value", field="email")
        assert error.field == "email"

    def test_token_limit_exceeded(self):
        error = TokenLimitExceededError(5000, 4096)
        assert error.current_tokens == 5000
        assert error.max_tokens == 4096
