"""
Database Engine & Session Management

Provides async SQLAlchemy engine, session factory, and base model.
Supports PostgreSQL (asyncpg) and SQLite (aiosqlite).
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, declarative_base

from app.config import settings

# ── Engine Creation ────────────────────────────────────
connect_args: dict = {}
engine_kwargs: dict = {
    "echo": settings.DEBUG,
    "pool_pre_ping": True,
}

if settings.DB_TYPE == "sqlite":
    # SQLite needs special handling for async
    connect_args["check_same_thread"] = False
    engine_kwargs["connect_args"] = connect_args
else:
    # PostgreSQL connection pooling
    engine_kwargs.update({
        "pool_size": 20,
        "max_overflow": 10,
        "pool_recycle": 3600,
    })

# Async engine
async_engine = create_async_engine(
    settings.db_url,
    **engine_kwargs,
)

# Sync engine (for Alembic / table creation)
sync_engine = create_engine(
    settings.db_url_sync,
    echo=settings.DEBUG,
    connect_args=connect_args if settings.DB_TYPE == "sqlite" else {},
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Base class for all ORM models
Base: DeclarativeBase = declarative_base()


async def get_db() -> AsyncSession:
    """
    FastAPI dependency that yields an async database session.

    Usage:
        @router.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables. For SQLite, also creates the data directory."""
    import os
    if settings.DB_TYPE == "sqlite":
        os.makedirs("data", exist_ok=True)

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose engine connections."""
    await async_engine.dispose()
    sync_engine.dispose()
