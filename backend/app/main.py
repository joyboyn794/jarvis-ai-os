"""
Jarvis AI OS — Application Entry Point

This module bootstraps the FastAPI application, mounts all routes,
configures middleware, and sets up the lifespan for startup/shutdown events.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.api.v1.router import api_router
from app.infrastructure.database import engine, Base
from app.infrastructure.redis import redis_client
from app.infrastructure.logging import setup_logging

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler.

    Startup:
    - Initialize logging
    - Verify database connectivity
    - Verify Redis connectivity
    - Warm up caches if needed

    Shutdown:
    - Close database connections
    - Close Redis connections
    - Flush pending logs
    """
    # ── Startup ──────────────────────────────────────────
    setup_logging()
    logger.info("🚀 Jarvis AI OS starting up...", environment=settings.APP_ENV)

    # Verify database connection
    async with engine.begin() as conn:
        await conn.execute(Base.metadata.select().limit(1))
    logger.info("✅ Database connected")

    # Verify Redis connection
    await redis_client.ping()
    logger.info("✅ Redis connected")

    yield

    # ── Shutdown ─────────────────────────────────────────
    logger.info("🛑 Jarvis AI OS shutting down...")
    await engine.dispose()
    await redis_client.close()
    logger.info("✅ Connections closed")


def create_app() -> FastAPI:
    """Factory function to create and configure the FastAPI application."""

    app = FastAPI(
        title="Jarvis AI OS",
        description="Intelligent modular AI assistant — Backend API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )

    # ── Middleware ───────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # ── Routes ───────────────────────────────────────────
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # ── Health Check ─────────────────────────────────────
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "jarvis", "version": "0.1.0"}

    # ── Global Exception Handler ─────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error("Unhandled exception", error=str(exc), path=str(request.url))
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "type": type(exc).__name__},
        )

    return app


app = create_app()
