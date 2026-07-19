"""
Memory Repository Implementation

Implements IMemoryRepository using SQLAlchemy async ORM + pgvector.
Provides semantic search via cosine similarity on vector embeddings.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import MemoryEntry, MemoryType
from app.domain.repositories import IMemoryRepository
from app.infrastructure.models import MemoryEntryModel


class MemoryRepository(IMemoryRepository):
    """SQLAlchemy + pgvector-based Memory repository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _to_domain(model: MemoryEntryModel) -> MemoryEntry:
        return MemoryEntry(
            id=model.id,
            user_id=model.user_id,
            content=model.content,
            embedding=list(model.embedding) if model.embedding is not None else None,
            memory_type=MemoryType(model.memory_type),
            importance=model.importance,
            access_count=model.access_count,
            last_accessed=model.last_accessed,
            metadata=model.metadata_ or {},
            created_at=model.created_at,
        )

    @staticmethod
    def _to_model(entity: MemoryEntry) -> MemoryEntryModel:
        return MemoryEntryModel(
            id=entity.id,
            user_id=entity.user_id,
            content=entity.content,
            embedding=entity.embedding,
            memory_type=entity.memory_type.value,
            importance=entity.importance,
            access_count=entity.access_count,
            last_accessed=entity.last_accessed,
            metadata_=entity.metadata,
            created_at=entity.created_at,
        )

    async def get_by_id(self, memory_id: UUID) -> Optional[MemoryEntry]:
        result = await self.session.execute(
            select(MemoryEntryModel).where(MemoryEntryModel.id == memory_id)
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def search_similar(
        self,
        user_id: UUID,
        embedding: List[float],
        limit: int = 10,
        threshold: float = 0.7,
        memory_type: Optional[str] = None,
    ) -> List[MemoryEntry]:
        """
        Search for memory entries by cosine similarity.

        Uses pgvector's <=> operator for cosine distance.
        Lower distance = higher similarity.
        """
        # Convert threshold (similarity) to distance:
        # cosine_distance = 1 - cosine_similarity
        max_distance = 1.0 - threshold

        query = (
            select(
                MemoryEntryModel,
                (1.0 - MemoryEntryModel.embedding.cosine_distance(embedding)).label(
                    "similarity"
                ),
            )
            .where(
                MemoryEntryModel.user_id == user_id,
                MemoryEntryModel.embedding.is_not(None),
            )
            .order_by(MemoryEntryModel.embedding.cosine_distance(embedding))
            .limit(limit)
        )

        if memory_type:
            query = query.where(MemoryEntryModel.memory_type == memory_type)

        result = await self.session.execute(query)
        rows = result.all()

        entries = []
        for model, _ in rows:
            entry = self._to_domain(model)
            entries.append(entry)

        return entries

    async def create(self, memory: MemoryEntry) -> MemoryEntry:
        model = self._to_model(memory)
        self.session.add(model)
        await self.session.flush()
        return self._to_domain(model)

    async def update(self, memory: MemoryEntry) -> MemoryEntry:
        model = await self.session.get(MemoryEntryModel, memory.id)
        if not model:
            raise ValueError(f"Memory entry {memory.id} not found")
        model.content = memory.content
        model.importance = memory.importance
        model.memory_type = memory.memory_type.value
        model.metadata_ = memory.metadata
        await self.session.flush()
        return self._to_domain(model)

    async def delete(self, memory_id: UUID) -> None:
        model = await self.session.get(MemoryEntryModel, memory_id)
        if model:
            await self.session.delete(model)
            await self.session.flush()

    async def touch(self, memory_id: UUID) -> None:
        """Update access statistics for a memory entry."""
        await self.session.execute(
            update(MemoryEntryModel)
            .where(MemoryEntryModel.id == memory_id)
            .values(
                access_count=MemoryEntryModel.access_count + 1,
                last_accessed=datetime.utcnow(),
            )
        )
        await self.session.flush()
