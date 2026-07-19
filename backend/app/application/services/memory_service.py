"""
Memory Service

Manages long-term memory with:
- Semantic storage and retrieval using vector embeddings
- Automatic memory consolidation from conversations
- Context injection for chat prompts
- Importance scoring and decay
"""

import uuid
from datetime import datetime
from typing import List, Optional

import structlog

from app.domain.entities import MemoryEntry, MemoryType
from app.domain.repositories import IMemoryRepository
from app.application.interfaces import IMemoryService, MemorySearchResult
from app.infrastructure.ai.openai_client import AIClient

logger = structlog.get_logger(__name__)

# Prompts for memory operations
MEMORY_EXTRACTION_PROMPT = """Extract key facts, preferences, and information about the user from this conversation.
Return a JSON array of memory items. Each item should have:
- "content": The factual statement (keep it concise)
- "type": One of "fact", "preference", "event", "skill"
- "importance": A float from 0.0 to 1.0 indicating how important this memory is

Only include genuinely useful information. Ignore trivial chitchat.

Conversation:
{conversation}

Output ONLY valid JSON array, nothing else:
"""

CONSOLIDATION_PROMPT = """Below are several related memories about a user.
Synthesize them into a single, concise, comprehensive summary.
Merge duplicate information. Keep the most important and recent details.

Memories:
{memories}

Synthesized summary:"""


class MemoryService(IMemoryService):
    """
    Manages the full lifecycle of user memories.

    Features:
    - Semantic search using OpenAI embeddings + pgvector
    - Automatic memory extraction from conversations
    - Memory consolidation (merging related memories)
    - Context building for chat prompts
    """

    def __init__(self, memory_repo: IMemoryRepository, ai_client: AIClient):
        self.memory_repo = memory_repo
        self.ai_client = ai_client

    async def store(
        self,
        user_id: uuid.UUID,
        content: str,
        memory_type: str = "fact",
        importance: float = 0.5,
    ) -> MemoryEntry:
        """
        Store a new memory with its embedding.

        Args:
            user_id: Owner of this memory.
            content: The memory text.
            memory_type: Classification (fact, preference, event, skill).
            importance: Importance score (0.0 - 1.0).
        """
        # Generate embedding
        embedding = await self.ai_client.create_embedding(content)

        # Validate memory_type
        try:
            mem_type = MemoryType(memory_type)
        except ValueError:
            mem_type = MemoryType.FACT

        memory = MemoryEntry(
            id=uuid.uuid4(),
            user_id=user_id,
            content=content,
            embedding=embedding,
            memory_type=mem_type,
            importance=min(1.0, max(0.0, importance)),
        )

        created = await self.memory_repo.create(memory)
        logger.debug("Memory stored", memory_id=str(created.id), type=memory_type)
        return created

    async def search(
        self,
        user_id: uuid.UUID,
        query: str,
        limit: int = 10,
        memory_type: Optional[str] = None,
    ) -> List[MemorySearchResult]:
        """
        Search memories by semantic similarity to the query.

        Args:
            user_id: Whose memories to search.
            query: Natural language search query.
            limit: Maximum results.
            memory_type: Optional filter by memory type.

        Returns:
            List of MemorySearchResult sorted by relevance.
        """
        # Generate query embedding
        embedding = await self.ai_client.create_embedding(query)

        # Search with pgvector
        entries = await self.memory_repo.search_similar(
            user_id=user_id,
            embedding=embedding,
            limit=limit,
            threshold=0.65,  # Minimum similarity threshold
            memory_type=memory_type,
        )

        results = []
        for entry in entries:
            # Calculate approximate similarity from the distance
            # (The distance is already filtered by threshold in the repo)
            results.append(
                MemorySearchResult(
                    entry=entry,
                    similarity=entry.importance,  # Fallback — real similarity is in DB
                )
            )

            # Update access stats
            await self.memory_repo.touch(entry.id)

        return results

    async def retrieve_context(
        self,
        user_id: uuid.UUID,
        query: str,
        limit: int = 5,
    ) -> str:
        """
        Build a formatted memory context string for chat prompts.

        Searches relevant memories and formats them as bullet points
        suitable for injection into a system prompt.
        """
        try:
            results = await self.search(user_id, query, limit=limit)

            if not results:
                return ""

            lines = []
            for result in results:
                entry = result.entry
                type_label = entry.memory_type.value.upper()
                lines.append(f"- [{type_label}] {entry.content}")

            return "\n".join(lines)

        except Exception as e:
            logger.warning("Failed to retrieve memory context", error=str(e))
            return ""

    async def extract_from_conversation(
        self,
        user_id: uuid.UUID,
        messages: List[dict],
    ) -> List[MemoryEntry]:
        """
        Analyze a conversation and extract important memories.

        Uses the LLM to identify factual statements, preferences,
        and other useful information worth remembering.
        """
        # Format conversation for the extraction prompt
        conversation_text = "\n".join(
            f"{msg['role'].upper()}: {msg['content']}"
            for msg in messages[-10:]  # Last 10 messages
        )

        try:
            response = await self.ai_client.chat_completion(
                messages=[
                    {
                        "role": "user",
                        "content": MEMORY_EXTRACTION_PROMPT.format(
                            conversation=conversation_text
                        ),
                    }
                ],
                temperature=0.3,  # Low temperature for consistent extraction
                max_tokens=1000,
            )

            content = response.choices[0].message.content
            import json

            items = json.loads(content)

            stored_entries = []
            for item in items:
                if not isinstance(item, dict) or "content" not in item:
                    continue
                entry = await self.store(
                    user_id=user_id,
                    content=item["content"],
                    memory_type=item.get("type", "fact"),
                    importance=item.get("importance", 0.5),
                )
                stored_entries.append(entry)

            logger.info(
                "Memories extracted from conversation",
                count=len(stored_entries),
            )
            return stored_entries

        except Exception as e:
            logger.error("Memory extraction failed", error=str(e))
            return []

    async def consolidate(self, user_id: uuid.UUID) -> None:
        """
        Consolidate related memories into summary entries.

        Groups memories by type, merges overlapping information,
        and creates concise summary memories. This keeps the
        memory store manageable over time.
        """
        for mem_type in MemoryType:
            # Retrieve all memories of this type
            # Use a generic query to find them
            dummy_embedding = [0.0] * 384
            entries = await self.memory_repo.search_similar(
                user_id=user_id,
                embedding=dummy_embedding,
                limit=100,
                threshold=0.0,  # Get everything
                memory_type=mem_type.value,
            )

            if len(entries) < 3:
                continue

            # Group content for consolidation
            memories_text = "\n".join(f"- {e.content}" for e in entries)

            try:
                response = await self.ai_client.chat_completion(
                    messages=[
                        {
                            "role": "user",
                            "content": CONSOLIDATION_PROMPT.format(
                                memories=memories_text
                            ),
                        }
                    ],
                    temperature=0.3,
                    max_tokens=500,
                )

                summary = response.choices[0].message.content.strip()
                if summary:
                    # Store consolidated memory
                    await self.store(
                        user_id=user_id,
                        content=summary,
                        memory_type=MemoryType.SUMMARY.value,
                        importance=0.8,
                    )

                    # Delete old individual memories
                    for entry in entries:
                        await self.memory_repo.delete(entry.id)

                    logger.info(
                        "Memory consolidated",
                        type=mem_type.value,
                        merged_count=len(entries),
                    )

            except Exception as e:
                logger.error("Memory consolidation failed", error=str(e), type=mem_type.value)
