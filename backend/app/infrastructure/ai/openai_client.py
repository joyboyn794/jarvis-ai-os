"""
AI Client Adapter — Multi-Provider

Supports:
- OpenAI: chat + embeddings + whisper + TTS
- Groq: chat (OpenAI-compatible API)
- Ollama: chat + embeddings (local)

Uses the OpenAI Python SDK for all providers since they all
implement OpenAI-compatible APIs (or use dedicated clients where needed).
"""

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


class AIClient:
    """
    Multi-provider AI client.

    Uses the OpenAI SDK with different base URLs depending on provider:
    - OpenAI: default base_url (api.openai.com)
    - Groq: https://api.groq.com/openai/v1
    - Ollama: http://localhost:11434/v1

    For embeddings:
    - OpenAI: uses text-embedding-ada-002
    - Groq/Ollama: uses local sentence-transformers (all-MiniLM-L6-v2)

    Voice (Whisper/TTS) is only available with OpenAI provider.
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
                api_key="ollama",  # Ollama doesn't need a real key
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
        """Setup embedding model — lazy loaded."""
        self._embedding_model = None
        self._embedding_dim = None

    async def _get_embedding_model(self):
        """Lazy-load the local embedding model for non-OpenAI providers."""
        if self._embedding_model is not None:
            return self._embedding_model

        if self.provider == "openai":
            return None  # Use OpenAI API

        try:
            from sentence_transformers import SentenceTransformer
            # all-MiniLM-L6-v2: 384 dims, ~80MB, fast on CPU
            model_name = "all-MiniLM-L6-v2"
            logger.info("Loading local embedding model", model=model_name)
            self._embedding_model = SentenceTransformer(model_name)
            self._embedding_dim = 384
            logger.info("Embedding model loaded", dims=self._embedding_dim)
            return self._embedding_model
        except ImportError:
            logger.error(
                "sentence-transformers not installed. "
                "Run: pip install sentence-transformers"
            )
            raise EmbeddingError(
                "Local embeddings require sentence-transformers. "
                "Run: pip install sentence-transformers"
            )

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

        Args:
            messages: List of message dicts with 'role' and 'content'.
            model: Model to use (defaults to provider default).
            tools: Optional tool definitions for function calling.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in the response.
            stream: Whether to stream the response.

        Returns:
            If stream=False: Complete ChatCompletion object.
            If stream=True: AsyncIterator of ChatCompletionChunk objects.
        """
        try:
            # Groq rate limits: ~30 req/min for free tier, model handles retries
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
            raise  # Let tenacity handle retries

        except Exception as e:
            logger.error("Chat completion failed", error=str(e))
            raise AIServiceError(f"Chat completion failed: {str(e)}") from e

    # ── Embeddings ────────────────────────────────────

    async def create_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding vector for the given text.

        Uses OpenAI API for 'openai' provider, or local sentence-transformers
        for 'groq' and 'ollama' (since they don't offer embeddings natively).

        Returns:
            Embedding vector (1536-dim for OpenAI, 384-dim for local).
        """
        # Truncate to ~8000 tokens
        if len(text) > 32000:
            text = text[:32000]

        try:
            if self.provider == "openai":
                response = await self.client.embeddings.create(
                    model=settings.OPENAI_EMBEDDING_MODEL,
                    input=text,
                )
                return response.data[0].embedding
            else:
                # Use local sentence-transformers
                model = await self._get_embedding_model()
                import asyncio
                embedding = await asyncio.to_thread(model.encode, text)
                return embedding.tolist()

        except Exception as e:
            logger.error("Embedding generation failed", error=str(e))
            raise EmbeddingError(f"Failed to create embedding: {str(e)}") from e

    # ── Voice ─────────────────────────────────────────

    async def transcribe_audio(
        self,
        audio_data: bytes,
        filename: str = "audio.wav",
        language: Optional[str] = None,
    ) -> str:
        """
        Transcribe audio to text.

        OpenAI provider: uses Whisper API.
        Other providers: raises NotImplementedError (use local Whisper instead).
        """
        if not self._supports_voice:
            raise AIServiceError(
                f"Voice transcription is not supported with '{self.provider}' provider. "
                "Use OpenAI provider or run Whisper locally."
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
        """
        Convert text to speech.

        OpenAI provider: uses OpenAI TTS.
        Other providers: raises NotImplementedError.
        """
        if not self._supports_voice:
            raise AIServiceError(
                f"TTS is not supported with '{self.provider}' provider. "
                "Use OpenAI provider or a local TTS engine."
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
