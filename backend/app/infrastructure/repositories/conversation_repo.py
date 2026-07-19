"""
Message & Conversation Repository Implementation

Implements IConversationRepository and IMessageRepository
using SQLAlchemy async ORM.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.entities import Conversation, Message, MessageRole
from app.domain.repositories import IConversationRepository, IMessageRepository
from app.infrastructure.models import ConversationModel, MessageModel


class MessageRepository(IMessageRepository):
    """SQLAlchemy-based Message repository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _to_domain(model: MessageModel) -> Message:
        return Message(
            id=model.id,
            conversation_id=model.conversation_id,
            role=MessageRole(model.role),
            content=model.content,
            tool_calls=model.tool_calls,
            tool_call_id=model.tool_call_id,
            token_count=model.token_count,
            created_at=model.created_at,
        )

    @staticmethod
    def _to_model(entity: Message) -> MessageModel:
        return MessageModel(
            id=entity.id,
            conversation_id=entity.conversation_id,
            role=entity.role.value,
            content=entity.content,
            tool_calls=entity.tool_calls,
            tool_call_id=entity.tool_call_id,
            token_count=entity.token_count,
            created_at=entity.created_at,
        )

    async def get_by_conversation(
        self,
        conversation_id: UUID,
        limit: int = 100,
        before: Optional[UUID] = None,
    ) -> List[Message]:
        query = (
            select(MessageModel)
            .where(MessageModel.conversation_id == conversation_id)
            .order_by(MessageModel.created_at.asc())
            .limit(limit)
        )
        if before:
            query = query.where(MessageModel.id < before)

        result = await self.session.execute(query)
        return [self._to_domain(m) for m in result.scalars().all()]

    async def create(self, message: Message) -> Message:
        model = self._to_model(message)
        self.session.add(model)
        await self.session.flush()
        return self._to_domain(model)

    async def create_batch(self, messages: List[Message]) -> List[Message]:
        models = [self._to_model(m) for m in messages]
        self.session.add_all(models)
        await self.session.flush()
        return [self._to_domain(m) for m in models]


class ConversationRepository(IConversationRepository):
    """SQLAlchemy-based Conversation repository."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._message_repo = MessageRepository(session)

    @staticmethod
    def _to_domain(model: ConversationModel) -> Conversation:
        return Conversation(
            id=model.id,
            user_id=model.user_id,
            title=model.title,
            model=model.model,
            metadata=model.metadata_ or {},
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _to_model(entity: Conversation) -> ConversationModel:
        return ConversationModel(
            id=entity.id,
            user_id=entity.user_id,
            title=entity.title,
            model=entity.model,
            metadata_=entity.metadata,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    async def get_by_id(self, conversation_id: UUID) -> Optional[Conversation]:
        result = await self.session.execute(
            select(ConversationModel)
            .where(ConversationModel.id == conversation_id)
            .options(selectinload(ConversationModel.messages))
        )
        model = result.scalar_one_or_none()
        if not model:
            return None

        conversation = self._to_domain(model)
        conversation.messages = [
            MessageRepository._to_domain(m) for m in (model.messages or [])
        ]
        return conversation

    async def list_by_user(
        self, user_id: UUID, limit: int = 50, offset: int = 0
    ) -> List[Conversation]:
        result = await self.session.execute(
            select(ConversationModel)
            .where(ConversationModel.user_id == user_id)
            .order_by(desc(ConversationModel.updated_at))
            .limit(limit)
            .offset(offset)
        )
        return [self._to_domain(m) for m in result.scalars().all()]

    async def create(self, conversation: Conversation) -> Conversation:
        model = self._to_model(conversation)
        self.session.add(model)
        await self.session.flush()
        return self._to_domain(model)

    async def update(self, conversation: Conversation) -> Conversation:
        model = await self.session.get(ConversationModel, conversation.id)
        if not model:
            raise ValueError(f"Conversation {conversation.id} not found")
        model.title = conversation.title
        model.model = conversation.model
        model.metadata_ = conversation.metadata
        await self.session.flush()
        return self._to_domain(model)

    async def delete(self, conversation_id: UUID) -> None:
        model = await self.session.get(ConversationModel, conversation_id)
        if model:
            await self.session.delete(model)
            await self.session.flush()
