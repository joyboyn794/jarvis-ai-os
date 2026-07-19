"""
Chat Service

Orchestrates multi-turn conversations with the LLM, manages
context windows, integrates long-term memory, and handles
tool/function calling.
"""

import json
import uuid
from typing import AsyncIterator, List, Optional

import structlog

from app.config import settings
from app.domain.entities import (
    Conversation,
    Message,
    MessageRole,
)
from app.domain.exceptions import (
    AIServiceError,
    ConversationNotFoundError,
    TokenLimitExceededError,
)
from app.domain.repositories import (
    IConversationRepository,
    IMessageRepository,
    IMemoryRepository,
)
from app.application.interfaces import (
    ChatRequest,
    ChatResponse,
    IChatService,
    IMemoryService,
)
from app.infrastructure.ai.openai_client import OpenAIClient

logger = structlog.get_logger(__name__)

# System prompt that defines Jarvis's personality
SYSTEM_PROMPT = """You are Jarvis, an advanced AI assistant inspired by Iron Man's AI.
You are intelligent, helpful, and efficient. Your responses are:
- Clear and concise, but thorough when needed
- Professional yet warm in tone
- Proactive in anticipating user needs
- Always honest about your limitations

You have access to:
- Long-term memory of past conversations
- The ability to execute computer commands (with user confirmation)
- Web search capabilities
- Task scheduling and reminders
- File management

When responding:
1. Address the user as "sir" or by their name if known
2. Be direct — avoid unnecessary preamble
3. When uncertain, ask clarifying questions rather than guessing
4. For complex tasks, break them into clear steps
"""


class ChatService(IChatService):
    """
    Manages chat conversations with context-aware LLM interactions.

    Responsibilities:
    - Creating and managing conversation sessions
    - Building context windows with message history + memory
    - Streaming responses back to the client
    - Token counting and context window management
    """

    def __init__(
        self,
        conversation_repo: IConversationRepository,
        message_repo: IMessageRepository,
        memory_service: IMemoryService,
        ai_client: OpenAIClient,
    ):
        self.conversation_repo = conversation_repo
        self.message_repo = message_repo
        self.memory_service = memory_service
        self.ai_client = ai_client

    # ── Helpers ─────────────────────────────────────────────

    async def _get_or_create_conversation(
        self, user_id: uuid.UUID, conversation_id: Optional[uuid.UUID]
    ) -> Conversation:
        """Fetch an existing conversation or create a new one."""
        if conversation_id:
            conv = await self.conversation_repo.get_by_id(conversation_id)
            if not conv:
                raise ConversationNotFoundError(str(conversation_id))
            if conv.user_id != user_id:
                raise ConversationNotFoundError(str(conversation_id))
            return conv

        # Create new conversation
        conv = Conversation(
            id=uuid.uuid4(),
            user_id=user_id,
            title="New Conversation",
            model=settings.OPENAI_MODEL,
        )
        return await self.conversation_repo.create(conv)

    async def _build_messages(
        self,
        user_id: uuid.UUID,
        conversation: Conversation,
        user_message: str,
        use_memory: bool = True,
    ) -> List[dict]:
        """
        Build the full message context for the LLM.

        Stack:
        1. System prompt
        2. Memory context (if enabled)
        3. Conversation history
        4. Current user message
        """
        messages = []

        # 1. System prompt
        system_content = SYSTEM_PROMPT

        # 2. Inject memory context
        if use_memory:
            try:
                memory_context = await self.memory_service.retrieve_context(
                    user_id, user_message
                )
                if memory_context:
                    system_content += f"\n\n## Relevant Context from Memory:\n{memory_context}"
            except Exception as e:
                logger.warning("Failed to load memory context", error=str(e))

        messages.append({"role": "system", "content": system_content})

        # 3. Conversation history (last 20 messages to manage context)
        history = await self.message_repo.get_by_conversation(
            conversation.id, limit=20
        )
        for msg in history:
            msg_dict = {"role": msg.role.value, "content": msg.content}
            if msg.tool_calls:
                msg_dict["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                msg_dict["tool_call_id"] = msg.tool_call_id
            messages.append(msg_dict)

        # 4. Current user message
        messages.append({"role": "user", "content": user_message})

        return messages

    def _estimate_tokens(self, messages: List[dict]) -> int:
        """Rough token count estimate (4 chars ≈ 1 token)."""
        total = 0
        for msg in messages:
            content = msg.get("content", "") or ""
            total += len(content) // 4
        return total

    def _auto_generate_title(self, user_message: str, assistant_response: str) -> str:
        """Generate a conversation title from the first exchange."""
        # Take first meaningful sentence from the user message
        title = user_message.strip()
        if len(title) > 50:
            # Try to break at a sentence boundary
            for delimiter in [". ", "? ", "! ", "\n"]:
                if delimiter in title[:60]:
                    title = title.split(delimiter)[0]
                    break
            else:
                title = title[:47] + "..."
        return title

    # ── Public Methods ──────────────────────────────────────

    async def send_message(
        self, user_id: uuid.UUID, request: ChatRequest
    ) -> ChatResponse:
        """
        Send a message and get a complete (non-streaming) response.

        Use this for synchronous operations like function calling
        or when the client cannot handle streaming.
        """
        conversation = await self._get_or_create_conversation(
            user_id, request.conversation_id
        )

        # Build context
        messages = await self._build_messages(
            user_id, conversation, request.message, request.use_memory
        )

        # Check token budget
        token_count = self._estimate_tokens(messages)
        if token_count > settings.OPENAI_MAX_TOKENS:
            raise TokenLimitExceededError(token_count, settings.OPENAI_MAX_TOKENS)

        # Save user message
        user_msg = Message(
            id=uuid.uuid4(),
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=request.message,
            token_count=len(request.message) // 4,
        )
        await self.message_repo.create(user_msg)

        # Get AI response
        try:
            response = await self.ai_client.chat_completion(
                messages=messages,
                model=request.model or conversation.model,
                stream=False,
            )
        except AIServiceError as e:
            logger.error("AI response failed", error=str(e))
            raise

        choice = response.choices[0]
        content = choice.message.content or ""
        total_tokens = response.usage.total_tokens if response.usage else 0

        # Save assistant message
        assistant_msg = Message(
            id=uuid.uuid4(),
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=content,
            token_count=len(content) // 4,
        )
        await self.message_repo.create(assistant_msg)

        # Auto-title if this is the first exchange
        if len(conversation.messages) == 0:
            conversation.title = self._auto_generate_title(request.message, content)
            await self.conversation_repo.update(conversation)

        return ChatResponse(
            conversation_id=conversation.id,
            message_id=assistant_msg.id,
            content=content,
            is_complete=True,
            tokens_used=total_tokens,
        )

    async def stream_message(
        self, user_id: uuid.UUID, request: ChatRequest
    ) -> AsyncIterator[ChatResponse]:
        """
        Send a message and stream the response token-by-token.

        This is the primary method for the real-time chat interface.
        Yields ChatResponse objects as tokens arrive.
        """
        conversation = await self._get_or_create_conversation(
            user_id, request.conversation_id
        )

        # Build context
        messages = await self._build_messages(
            user_id, conversation, request.message, request.use_memory
        )

        # Check token budget
        token_count = self._estimate_tokens(messages)
        if token_count > settings.OPENAI_MAX_TOKENS:
            raise TokenLimitExceededError(token_count, settings.OPENAI_MAX_TOKENS)

        # Save user message
        user_msg = Message(
            id=uuid.uuid4(),
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=request.message,
            token_count=len(request.message) // 4,
        )
        await self.message_repo.create(user_msg)

        # Stream AI response
        assistant_msg_id = uuid.uuid4()
        full_content = ""
        total_tokens = 0
        is_first_exchange = len(conversation.messages) == 0

        try:
            stream = await self.ai_client.chat_completion(
                messages=messages,
                model=request.model or conversation.model,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta:
                    delta = chunk.choices[0].delta
                    content_delta = delta.content or ""
                    full_content += content_delta

                    yield ChatResponse(
                        conversation_id=conversation.id,
                        message_id=assistant_msg_id,
                        content=content_delta,
                        is_complete=False,
                    )

                if chunk.usage:
                    total_tokens = chunk.usage.total_tokens

        except AIServiceError as e:
            logger.error("AI streaming failed", error=str(e))
            yield ChatResponse(
                conversation_id=conversation.id,
                message_id=assistant_msg_id,
                content=f"\n\n[Error: {str(e)}]",
                is_complete=False,
            )
            full_content += f"\n\n[Error: {str(e)}]"

        # Save complete assistant message
        assistant_msg = Message(
            id=assistant_msg_id,
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=full_content,
            token_count=len(full_content) // 4,
        )
        await self.message_repo.create(assistant_msg)

        # Auto-title on first exchange
        if is_first_exchange:
            conversation.title = self._auto_generate_title(request.message, full_content)
            await self.conversation_repo.update(conversation)

        # Yield final completion marker
        yield ChatResponse(
            conversation_id=conversation.id,
            message_id=assistant_msg_id,
            content="",
            is_complete=True,
            tokens_used=total_tokens,
        )

    async def get_conversation(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID
    ) -> Conversation:
        """Get a conversation with all messages, verifying ownership."""
        conv = await self.conversation_repo.get_by_id(conversation_id)
        if not conv or conv.user_id != user_id:
            raise ConversationNotFoundError(str(conversation_id))
        return conv

    async def list_conversations(
        self, user_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> List[Conversation]:
        """List conversations for a user, newest first."""
        return await self.conversation_repo.list_by_user(user_id, limit, offset)

    async def delete_conversation(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        """Delete a conversation, verifying ownership."""
        conv = await self.conversation_repo.get_by_id(conversation_id)
        if not conv or conv.user_id != user_id:
            raise ConversationNotFoundError(str(conversation_id))
        await self.conversation_repo.delete(conversation_id)
        logger.info("Conversation deleted", conversation_id=str(conversation_id))
