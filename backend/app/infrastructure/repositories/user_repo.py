"""
User Repository Implementation

Implements IUserRepository using SQLAlchemy async ORM.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.entities import User
from app.domain.repositories import IUserRepository
from app.infrastructure.models import UserModel


class UserRepository(IUserRepository):
    """SQLAlchemy-based User repository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _to_domain(model: UserModel) -> User:
        """Map ORM model to domain entity."""
        return User(
            id=model.id,
            email=model.email,
            display_name=model.display_name,
            password_hash=model.password_hash,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _to_model(entity: User) -> UserModel:
        """Map domain entity to ORM model."""
        return UserModel(
            id=entity.id,
            email=entity.email,
            display_name=entity.display_name,
            password_hash=entity.password_hash,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        result = await self.session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(
            select(UserModel).where(UserModel.email == email)
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def create(self, user: User) -> User:
        model = self._to_model(user)
        self.session.add(model)
        await self.session.flush()
        return self._to_domain(model)

    async def update(self, user: User) -> User:
        model = await self.session.get(UserModel, user.id)
        if not model:
            raise ValueError(f"User {user.id} not found")
        model.display_name = user.display_name
        model.is_active = user.is_active
        await self.session.flush()
        return self._to_domain(model)

    async def delete(self, user_id: UUID) -> None:
        model = await self.session.get(UserModel, user_id)
        if model:
            await self.session.delete(model)
            await self.session.flush()
