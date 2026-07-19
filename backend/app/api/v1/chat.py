"""
Chat Routes

REST endpoints for conversation management and the WebSocket
endpoint for real-time streaming chat.
"""

import json
import uuid
from typing import List, Optional

import structlog
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)

from app.domain.entities import User
from app.domain.exceptions import ConversationNotFoundError
from app.application.interfaces import ChatRequest as ChatReqDTO
from app.application.services.chat_service import ChatService
from app.api.schemas import (
    ChatRequest,
    ConversationDetailResponse,
    ConversationResponse,
    MessageResponse,
    ErrorResponse,
)
from app.api.dependencies import get_chat_service
from app.api.auth_utils import get_current_user

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.get(
    "/conversations",
    response_model=List[ConversationResponse],
)
async def list_conversations(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    """
    List all conversations for the current user.

    Returns conversations sorted by most recently updated first.
    """
    conversations = await chat_service.list_conversations(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )

    return [
        ConversationResponse(
            id=c.id,
            title=c.title,
            model=c.model,
            message_count=len(c.messages),
            last_message=c.messages[-1].content[:100] if c.messages else None,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in conversations
    ]


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    """
    Get a conversation with all its messages.
    """
    try:
        conv = await chat_service.get_conversation(conversation_id, current_user.id)
    except ConversationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    return ConversationDetailResponse(
        id=conv.id,
        title=conv.title,
        model=conv.model,
        messages=[
            MessageResponse(
                id=m.id,
                conversation_id=m.conversation_id,
                role=m.role.value,
                content=m.content,
                token_count=m.token_count,
                created_at=m.created_at,
            )
            for m in conv.messages
        ],
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse}},
)
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    """
    Delete a conversation and all its messages.
    """
    try:
        await chat_service.delete_conversation(conversation_id, current_user.id)
    except ConversationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )


@router.post(
    "/send",
    response_model=MessageResponse,
    responses={400: {"model": ErrorResponse}},
)
async def send_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    """
    Send a message and get a complete (non-streaming) response.

    For streaming responses, use the WebSocket endpoint instead.
    """
    chat_req = ChatReqDTO(
        conversation_id=request.conversation_id,
        message=request.message,
        model=request.model,
        stream=False,
        use_memory=request.use_memory,
    )

    try:
        response = await chat_service.send_message(current_user.id, chat_req)
    except ConversationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    return MessageResponse(
        id=response.message_id,
        conversation_id=response.conversation_id,
        role="assistant",
        content=response.content,
        token_count=response.tokens_used,
    )


# ── WebSocket for Streaming Chat ────────────────────────────

@router.websocket("/ws")
async def websocket_chat(
    websocket: WebSocket,
    token: str = Query(...),
    chat_service: ChatService = Depends(get_chat_service),
):
    """
    WebSocket endpoint for real-time streaming chat.

    Authentication is via query parameter `token`.

    Client sends JSON messages:
    {
        "type": "message",
        "conversation_id": "uuid-or-null",
        "message": "user message text",
        "use_memory": true
    }

    Server sends JSON events:
    {
        "type": "token",
        "conversation_id": "uuid",
        "content": "partial token text"
    }
    {
        "type": "done",
        "conversation_id": "uuid",
        "message_id": "uuid",
        "tokens_used": 123
    }
    {
        "type": "error",
        "message": "error description"
    }
    """
    from app.api.dependencies import get_auth_service

    # Authenticate via token
    try:
        auth_service = get_auth_service()
        user = await auth_service.get_current_user(token)
    except Exception:
        await websocket.close(code=4001, reason="Authentication failed")
        return

    await websocket.accept()
    logger.info("WebSocket connected", user_id=str(user.id))

    try:
        while True:
            # Receive message from client
            raw = await websocket.receive_text()
            data = json.loads(raw)

            if data.get("type") != "message":
                await websocket.send_json({"type": "error", "message": "Unknown message type"})
                continue

            message_text = data.get("message", "")
            conversation_id_str = data.get("conversation_id")
            use_memory = data.get("use_memory", True)

            if not message_text:
                await websocket.send_json({"type": "error", "message": "Empty message"})
                continue

            conversation_id = uuid.UUID(conversation_id_str) if conversation_id_str else None

            chat_req = ChatReqDTO(
                conversation_id=conversation_id,
                message=message_text,
                stream=True,
                use_memory=use_memory,
            )

            try:
                async for chunk in chat_service.stream_message(user.id, chat_req):
                    if chunk.is_complete:
                        await websocket.send_json({
                            "type": "done",
                            "conversation_id": str(chunk.conversation_id),
                            "message_id": str(chunk.message_id),
                            "tokens_used": chunk.tokens_used,
                        })
                    else:
                        await websocket.send_json({
                            "type": "token",
                            "conversation_id": str(chunk.conversation_id),
                            "content": chunk.content,
                        })

            except Exception as e:
                logger.error("Stream error", error=str(e))
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                })

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", user_id=str(user.id))
    except Exception as e:
        logger.error("WebSocket error", error=str(e))
        try:
            await websocket.close()
        except Exception:
            pass
