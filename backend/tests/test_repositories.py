"""
Unit Tests — Repository Layer

Tests for SQLAlchemy repository implementations.
Uses SQLite in-memory for fast, isolated testing.
"""

import uuid
import pytest

from app.domain.entities import (
    User,
    Message,
    MessageRole,
    Conversation,
    MemoryEntry,
    MemoryType,
)
from app.infrastructure.repositories import (
    UserRepository,
    ConversationRepository,
    MessageRepository,
    MemoryRepository,
)


class TestUserRepository:
    """Tests for UserRepository CRUD operations."""

    async def test_create_and_get_by_id(self, user_repo):
        user = User(
            id=uuid.uuid4(),
            email="repo-test@example.com",
            display_name="Repo Test",
            password_hash="hash123",
        )
        created = await user_repo.create(user)
        assert created.email == "repo-test@example.com"

        fetched = await user_repo.get_by_id(user.id)
        assert fetched is not None
        assert fetched.email == "repo-test@example.com"

    async def test_get_by_email(self, user_repo):
        user = User(
            id=uuid.uuid4(),
            email="email-lookup@example.com",
            display_name="Email Lookup",
            password_hash="hash123",
        )
        await user_repo.create(user)

        fetched = await user_repo.get_by_email("email-lookup@example.com")
        assert fetched is not None

        not_found = await user_repo.get_by_email("nonexistent@example.com")
        assert not_found is None

    async def test_update_user(self, user_repo):
        user = User(
            id=uuid.uuid4(),
            email="update-test@example.com",
            display_name="Original Name",
            password_hash="hash123",
        )
        await user_repo.create(user)

        user.display_name = "Updated Name"
        updated = await user_repo.update(user)
        assert updated.display_name == "Updated Name"

    async def test_delete_user(self, user_repo):
        user = User(
            id=uuid.uuid4(),
            email="delete-test@example.com",
            display_name="Delete Me",
            password_hash="hash123",
        )
        await user_repo.create(user)
        await user_repo.delete(user.id)

        fetched = await user_repo.get_by_id(user.id)
        assert fetched is None


class TestConversationRepository:
    """Tests for ConversationRepository CRUD operations."""

    async def test_create_conversation(self, conversation_repo, user_repo):
        # Create a user first
        user = User(
            id=uuid.uuid4(),
            email="conv-user@example.com",
            display_name="Conv User",
            password_hash="hash",
        )
        await user_repo.create(user)

        conv = Conversation(
            id=uuid.uuid4(),
            user_id=user.id,
            title="Test Conversation",
        )
        created = await conversation_repo.create(conv)
        assert created.title == "Test Conversation"

    async def test_list_by_user(self, conversation_repo, user_repo):
        user = User(
            id=uuid.uuid4(),
            email="list-user@example.com",
            display_name="List User",
            password_hash="hash",
        )
        await user_repo.create(user)

        # Create multiple conversations
        for i in range(3):
            conv = Conversation(
                id=uuid.uuid4(),
                user_id=user.id,
                title=f"Conversation {i}",
            )
            await conversation_repo.create(conv)

        conversations = await conversation_repo.list_by_user(user.id)
        assert len(conversations) == 3


class TestMessageRepository:
    """Tests for MessageRepository CRUD operations."""

    async def test_create_and_retrieve_messages(
        self, message_repo, conversation_repo, user_repo
    ):
        user = User(
            id=uuid.uuid4(),
            email="msg-user@example.com",
            display_name="Msg User",
            password_hash="hash",
        )
        await user_repo.create(user)

        conv = Conversation(
            id=uuid.uuid4(),
            user_id=user.id,
            title="Message Test",
        )
        await conversation_repo.create(conv)

        msg = Message(
            id=uuid.uuid4(),
            conversation_id=conv.id,
            role=MessageRole.USER,
            content="Test message",
        )
        created = await message_repo.create(msg)
        assert created.content == "Test message"

        messages = await message_repo.get_by_conversation(conv.id)
        assert len(messages) == 1
        assert messages[0].role == MessageRole.USER

    async def test_create_batch(self, message_repo, conversation_repo, user_repo):
        user = User(
            id=uuid.uuid4(),
            email="batch-user@example.com",
            display_name="Batch User",
            password_hash="hash",
        )
        await user_repo.create(user)

        conv = Conversation(
            id=uuid.uuid4(),
            user_id=user.id,
            title="Batch Test",
        )
        await conversation_repo.create(conv)

        messages = [
            Message(
                id=uuid.uuid4(),
                conversation_id=conv.id,
                role=MessageRole.USER,
                content=f"Message {i}",
            )
            for i in range(5)
        ]
        created_batch = await message_repo.create_batch(messages)
        assert len(created_batch) == 5

        all_messages = await message_repo.get_by_conversation(conv.id)
        assert len(all_messages) == 5


class TestMemoryRepository:
    """Tests for MemoryRepository vector operations."""

    async def test_create_memory(self, memory_repo, user_repo):
        user = User(
            id=uuid.uuid4(),
            email="memory-user@example.com",
            display_name="Memory User",
            password_hash="hash",
        )
        await user_repo.create(user)

        entry = MemoryEntry(
            id=uuid.uuid4(),
            user_id=user.id,
            content="User prefers dark mode",
            memory_type=MemoryType.PREFERENCE,
            importance=0.9,
        )
        created = await memory_repo.create(entry)
        assert created.content == "User prefers dark mode"
        assert created.memory_type == MemoryType.PREFERENCE

    async def test_touch_updates_access_stats(self, memory_repo, user_repo):
        user = User(
            id=uuid.uuid4(),
            email="touch-user@example.com",
            display_name="Touch User",
            password_hash="hash",
        )
        await user_repo.create(user)

        entry = MemoryEntry(
            id=uuid.uuid4(),
            user_id=user.id,
            content="Some memory",
        )
        created = await memory_repo.create(entry)
        assert created.access_count == 0

        await memory_repo.touch(created.id)

        updated = await memory_repo.get_by_id(created.id)
        assert updated.access_count == 1
        assert updated.last_accessed is not None
