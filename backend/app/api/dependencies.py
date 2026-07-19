"""
Dependency Injection Container

Centralized wiring of all dependencies. Uses FastAPI's Depends()
system to provide service instances to route handlers.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.infrastructure.ai.openai_client import openai_client, OpenAIClient
from app.infrastructure.repositories import (
    UserRepository,
    ConversationRepository,
    MessageRepository,
    MemoryRepository,
)
from app.application.services.auth_service import AuthService
from app.application.services.chat_service import ChatService
from app.application.services.memory_service import MemoryService


def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    """Get UserRepository instance."""
    return UserRepository(db)


def get_conversation_repository(db: AsyncSession = Depends(get_db)) -> ConversationRepository:
    """Get ConversationRepository instance."""
    return ConversationRepository(db)


def get_message_repository(db: AsyncSession = Depends(get_db)) -> MessageRepository:
    """Get MessageRepository instance."""
    return MessageRepository(db)


def get_memory_repository(db: AsyncSession = Depends(get_db)) -> MemoryRepository:
    """Get MemoryRepository instance."""
    return MemoryRepository(db)


def get_ai_client() -> OpenAIClient:
    """Get the OpenAI client singleton."""
    return openai_client


def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repository),
) -> AuthService:
    """Get AuthService with its dependencies."""
    return AuthService(user_repo=user_repo)


def get_memory_service(
    memory_repo: MemoryRepository = Depends(get_memory_repository),
    ai_client: OpenAIClient = Depends(get_ai_client),
) -> MemoryService:
    """Get MemoryService with its dependencies."""
    return MemoryService(memory_repo=memory_repo, ai_client=ai_client)


def get_chat_service(
    conversation_repo: ConversationRepository = Depends(get_conversation_repository),
    message_repo: MessageRepository = Depends(get_message_repository),
    memory_service: MemoryService = Depends(get_memory_service),
    ai_client: OpenAIClient = Depends(get_ai_client),
) -> ChatService:
    """Get ChatService with its dependencies."""
    return ChatService(
        conversation_repo=conversation_repo,
        message_repo=message_repo,
        memory_service=memory_service,
        ai_client=ai_client,
    )
