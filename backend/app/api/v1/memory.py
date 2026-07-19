"""
Memory Routes

Endpoints for storing and searching long-term memories.
"""

from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.domain.entities import User
from app.api.schemas import (
    MemoryEntryResponse,
    MemorySearchRequest,
    MemorySearchResultResponse,
    ErrorResponse,
)
from app.api.dependencies import get_memory_service
from app.api.auth_utils import get_current_user
from app.application.services.memory_service import MemoryService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/memory", tags=["Memory"])


@router.post(
    "/search",
    response_model=List[MemorySearchResultResponse],
)
async def search_memories(
    request: MemorySearchRequest,
    current_user: User = Depends(get_current_user),
    memory_service: MemoryService = Depends(get_memory_service),
):
    """
    Search memories semantically by query text.

    Returns memories ranked by relevance to the query.
    """
    results = await memory_service.search(
        user_id=current_user.id,
        query=request.query,
        limit=request.limit,
        memory_type=request.memory_type,
    )

    return [
        MemorySearchResultResponse(
            entry=MemoryEntryResponse(
                id=r.entry.id,
                content=r.entry.content,
                memory_type=r.entry.memory_type.value,
                importance=r.entry.importance,
                access_count=r.entry.access_count,
                created_at=r.entry.created_at,
            ),
            similarity=r.similarity,
        )
        for r in results
    ]


@router.post(
    "/store",
    response_model=MemoryEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def store_memory(
    content: str = Query(..., min_length=1, max_length=5000),
    memory_type: str = Query("fact", pattern="^(fact|preference|event|skill)$"),
    importance: float = Query(0.5, ge=0.0, le=1.0),
    current_user: User = Depends(get_current_user),
    memory_service: MemoryService = Depends(get_memory_service),
):
    """
    Manually store a memory entry.

    The memory will be embedded and available for future semantic searches.
    """
    entry = await memory_service.store(
        user_id=current_user.id,
        content=content,
        memory_type=memory_type,
        importance=importance,
    )

    return MemoryEntryResponse(
        id=entry.id,
        content=entry.content,
        memory_type=entry.memory_type.value,
        importance=entry.importance,
        access_count=entry.access_count,
        created_at=entry.created_at,
    )


@router.post(
    "/consolidate",
    status_code=status.HTTP_202_ACCEPTED,
)
async def consolidate_memories(
    current_user: User = Depends(get_current_user),
    memory_service: MemoryService = Depends(get_memory_service),
):
    """
    Trigger memory consolidation for the current user.

    This merges related memories into concise summaries and
    removes redundant individual entries. Useful for keeping
    the memory store clean and relevant.
    """
    await memory_service.consolidate(current_user.id)
    return {"status": "consolidation started"}
