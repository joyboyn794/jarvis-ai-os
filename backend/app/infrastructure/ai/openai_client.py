"""
OpenAI Client Adapter

Encapsulates all OpenAI API interactions including:
- Chat completions (streaming and non-streaming)
- Embedding generation
- Speech-to-text (Whisper)
- Text-to-speech

Implements retry logic via tenacity for resilience.
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


class OpenAIClient:
    """
    Async wrapper around the OpenAI SDK.

    Provides:
    - Chat completions with streaming support
    - Embedding generation for semantic search
    - Speech-to-text via Whisper
    - Text-to-speech
    """

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.default_model = settings.OPENAI_MODEL

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
        Send a chat completion request to OpenAI.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            model: Model to use (defaults to settings.OPENAI_MODEL).
            tools: Optional tool definitions for function calling.
            temperature: Sampling temperature (defaults to settings).
            max_tokens: Maximum tokens in the response.
            stream: Whether to stream the response.

        Returns:
            If stream=False: Complete ChatCompletion object.
            If stream=True: AsyncIterator of ChatCompletionChunk objects.

        Raises:
            AIServiceError: On non-retryable API failures.
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
            raise  # Let tenacity handle retries

        except Exception as e:
            logger.error("OpenAI chat completion failed", error=str(e))
            raise AIServiceError(f"Chat completion failed: {str(e)}") from e

    @retry(
        retry=retry_if_exception_type((RateLimitError, APIConnectionError)),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def create_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding vector for the given text.

        Args:
            text: Input text to embed (will be truncated if too long).

        Returns:
            1536-dimensional embedding vector.

        Raises:
            EmbeddingError: If embedding generation fails.
        """
        try:
            # Truncate to ~8000 tokens to stay within model limits
            if len(text) > 32000:
                text = text[:32000]

            response = await self.client.embeddings.create(
                model=settings.OPENAI_EMBEDDING_MODEL,
                input=text,
            )
            return response.data[0].embedding

        except Exception as e:
            logger.error("Embedding generation failed", error=str(e))
            raise EmbeddingError(f"Failed to create embedding: {str(e)}") from e

    async def transcribe_audio(
        self,
        audio_data: bytes,
        filename: str = "audio.wav",
        language: Optional[str] = None,
    ) -> str:
        """
        Transcribe audio using OpenAI Whisper.

        Args:
            audio_data: Raw audio bytes (WAV, MP3, etc.).
            filename: Filename hint for format detection.
            language: ISO language code (e.g., 'en', 'fa').

        Returns:
            Transcribed text.
        """
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
        Generate speech audio from text using OpenAI TTS.

        Args:
            text: Text to convert to speech (max 4096 chars).
            voice: Voice name (alloy, echo, fable, onyx, nova, shimmer).
            speed: Playback speed (0.25 to 4.0).

        Returns:
            MP3 audio bytes.
        """
        try:
            # Truncate text to TTS limit
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
openai_client = OpenAIClient()
