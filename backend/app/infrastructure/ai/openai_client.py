"""
AI Client Adapter — Multi-Provider

Supports:
- OpenAI: chat + embeddings + whisper + TTS
- Groq: chat (OpenAI-compatible API)
- Ollama: chat + embeddings (local)

Uses the OpenAI Python SDK for all providers since they all
implement OpenAI-compatible APIs (or use dedicated clients where needed).
"""

import hashlib
import struct
from typing import AsyncIterator, List, Optional
import structlog
from openai import AsyncOpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.config import settings
from app.domain.exceptions import AIServiceError, EmbeddingError

logger = structlog.get_logger(__name__)

# Retryable exceptions
from openai import (
    RateLimitError,
    APITimeoutError,
    APIConnectionError,
    InternalServerError,
)

# Embedding dimension for local fallback (matches all-MiniLM-L6-v2)
_LOCAL_EMBEDDING_DIM = 384


def _hash_embedding(text: str, dim: int = _LOCAL_EMBEDDING_DIM) -> List[float]:
    """
    Simple hash-based embedding — zero dependencies.

    Uses SHA-256 to produce a deterministic fixed-size vector.
    NOT semantically meaningful, but allows the app to function.
    Install sentence-transformers for real semantic embeddings:
        pip install sentence-transformers
    """
    # Normalize
    text = text.lower().strip()[:4000]
    vec = [0.0] * dim

    for i in range(dim):
        h = hashlib.sha256(f"{text}:{i}".encode()).digest()
        # Convert 4 bytes to a float in [-1, 1]
        val = struct.unpack('>i', h[:4])[0] / 2147483647.0
        vec[i] = val

    # Normalize to unit length
    norm = sum(v * v for v in vec) ** 0.5
    if norm > 0:
        vec = [v / norm for v in vec]

    return vec


class AIClient:
    """
    Multi-provider AI client.

    Providers:
    - OpenAI: chat + embeddings + whisper + TTS
    - Groq: chat (fast, free tier)
    - Ollama: chat + embeddings (local)

    Embeddings:
    - OpenAI: uses text-embedding-ada-002
    - Groq/Ollama without sentence-transformers: fallback hash-based
    - Groq/Ollama with sentence-transformers: all-MiniLM-L6-v2 (semantic)
    """

    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()
        self._setup_client()
        self._setup_embeddings()

    def _setup_client(self):
        """Create the chat client based on provider."""
        if self.provider == "groq":
            if not settings.GROQ_API_KEY:
                raise AIServiceError(
                    "GROQ_API_KEY is required when LLM_PROVIDER=groq. "
                    "Get a free key at https://console.groq.com/keys"
                )
            self.client = AsyncOpenAI(
                api_key=settings.GROQ_API_KEY,
                base_url="https://api.groq.com/openai/v1",
            )
            self.default_model = settings.GROQ_MODEL
            self._supports_voice = False
            logger.info("AI Client initialized", provider="groq", model=self.default_model)

        elif self.provider == "ollama":
            self.client = AsyncOpenAI(
                api_key="ollama",
                base_url="http://localhost:11434/v1",
            )
            self.default_model = settings.OPENAI_MODEL or "llama3.1:8b"
            self._supports_voice = False
            logger.info("AI Client initialized", provider="ollama", model=self.default_model)

        else:  # openai
            if not settings.OPENAI_API_KEY:
                raise AIServiceError(
                    "OPENAI_API_KEY is required when LLM_PROVIDER=openai."
                )
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            self.default_model = settings.OPENAI_MODEL
            self._supports_voice = True
            logger.info("AI Client initialized", provider="openai", model=self.default_model)

    def _setup_embeddings(self):
        """Try to load sentence-transformers; fall back to hash-based."""
        self._st_model = None
        self._embedding_dim = _LOCAL_EMBEDDING_DIM
        self._embedding_mode = "hash"  # hash | st | openai

        if self.provider == "openai":
            self._embedding_mode = "openai"
            return

        try:
            from sentence_transformers import SentenceTransformer
            self._st_model = SentenceTransformer("all-MiniLM-L6-v2")
            self._embedding_dim = 384
            self._embedding_mode = "st"
            logger.info("Using sentence-transformers for embeddings", dim=384)
        except (ImportError, OSError) as e:
            logger.warning(
                "sentence-transformers not available, using fallback hash embeddings",
                reason=str(e)[:120],
                hint="Install with: pip install sentence-transformers",
            )
            self._embedding_mode = "hash"

    # ── Chat Completions ──────────────────────────────

    @retry(
        retry=retry_if_exception_type(
            (RateLimitError, APITimeoutError, APIConnectionError, InternalServerError)
        ),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def chat_completion(
        self,
        messages: List[dict],
        model: Optional[str] = None,
        tools: Optional[List[dict]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ):
        """
        Send a chat completion request.
        """
        try:
            response = await self.client.chat.completions.create(
                model=model or self.default_model,
                messages=messages,
                tools=tools,
                temperature=temperature or settings.OPENAI_TEMPERATURE,
                max_tokens=max_tokens or settings.OPENAI_MAX_TOKENS,
                stream=stream,
            )
            return response

        except (RateLimitError, APITimeoutError, APIConnectionError, InternalServerError):
            raise

        except Exception as e:
            logger.error("Chat completion failed", error=str(e))
            raise AIServiceError(f"Chat completion failed: {str(e)}") from e

    # ── Embeddings ────────────────────────────────────

    async def create_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding vector.

        Provider strategy:
        - OpenAI → text-embedding-ada-002 API (1536-dim)
        - sentence-transformers installed → all-MiniLM-L6-v2 (384-dim, semantic)
        - No sentence-transformers → hash-based (384-dim, NOT semantic)
        """
        if len(text) > 32000:
            text = text[:32000]

        try:
            if self._embedding_mode == "openai":
                response = await self.client.embeddings.create(
                    model=settings.OPENAI_EMBEDDING_MODEL,
                    input=text,
                )
                return response.data[0].embedding

            elif self._embedding_mode == "st":
                import asyncio
                embedding = await asyncio.to_thread(self._st_model.encode, text)
                return embedding.tolist()

            else:
                # Hash fallback — functional but not semantic
                return _hash_embedding(text, self._embedding_dim)

        except Exception as e:
            logger.error("Embedding generation failed", error=str(e))
            raise EmbeddingError(f"Failed to create embedding: {str(e)}") from e

    @property
    def embedding_dimension(self) -> int:
        """Current embedding dimension."""
        if self._embedding_mode == "openai":
            return 1536
        return self._embedding_dim

    @property
    def using_semantic_embeddings(self) -> bool:
        """Whether embeddings are semantically meaningful."""
        return self._embedding_mode in ("openai", "st")

    # ── Voice ─────────────────────────────────────────

    async def transcribe_audio(
        self,
        audio_data: bytes,
        filename: str = "audio.wav",
        language: Optional[str] = None,
    ) -> str:
        """Transcribe audio (OpenAI provider only)."""
        if not self._supports_voice:
            raise AIServiceError(
                f"Voice transcription is not supported with '{self.provider}' provider."
            )

        import io
        try:
            audio_file = io.BytesIO(audio_data)
            audio_file.name = filename
            kwargs = {"model": "whisper-1", "file": audio_file}
            if language:
                kwargs["language"] = language
            response = await self.client.audio.transcriptions.create(**kwargs)
            return response.text
        except Exception as e:
            logger.error("Audio transcription failed", error=str(e))
            raise AIServiceError(f"Transcription failed: {str(e)}") from e

    async def text_to_speech(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: float = 1.0,
    ) -> bytes:
        """Convert text to speech (OpenAI provider only)."""
        if not self._supports_voice:
            raise AIServiceError(
                f"TTS is not supported with '{self.provider}' provider."
            )
        try:
            text = text[:4096]
            response = await self.client.audio.speech.create(
                model="tts-1",
                voice=voice or settings.TTS_VOICE,
                input=text,
                speed=speed,
            )
            return response.content
        except Exception as e:
            logger.error("Text-to-speech failed", error=str(e))
            raise AIServiceError(f"TTS failed: {str(e)}") from e

    async def close(self):
        """Close the underlying HTTP client."""
        await self.client.close()


# Global singleton
ai_client = AIClient()
