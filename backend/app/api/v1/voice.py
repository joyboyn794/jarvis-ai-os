"""
Voice Routes

Endpoints for speech-to-text and text-to-speech operations.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from fastapi.responses import Response

from app.domain.entities import User
from app.infrastructure.ai.openai_client import OpenAIClient
from app.api.dependencies import get_ai_client
from app.api.auth_utils import get_current_user

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/voice", tags=["Voice"])


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = Query(default=None, max_length=5),
    current_user: User = Depends(get_current_user),
    ai_client: OpenAIClient = Depends(get_ai_client),
):
    """
    Transcribe audio to text using OpenAI Whisper.

    Supports WAV, MP3, MP4, M4A, OGG, WEBM, and FLAC formats.
    Maximum file size: 25MB.

    Args:
        file: Audio file to transcribe.
        language: Optional ISO language code (e.g., 'en', 'fa').

    Returns:
        {"text": "transcribed text"}
    """
    if file.content_type and not file.content_type.startswith(("audio/", "video/")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported content type: {file.content_type}",
        )

    try:
        audio_data = await file.read()

        # Check file size (25MB limit for Whisper)
        if len(audio_data) > 25 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Audio file must be less than 25MB",
            )

        text = await ai_client.transcribe_audio(
            audio_data=audio_data,
            filename=file.filename or "audio.wav",
            language=language,
        )

        logger.info("Audio transcribed", user_id=str(current_user.id))
        return {"text": text}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Transcription failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription failed: {str(e)}",
        )


@router.post("/speak")
async def text_to_speech(
    text: str = Query(..., min_length=1, max_length=4096),
    voice: str = Query("alloy", pattern="^(alloy|echo|fable|onyx|nova|shimmer)$"),
    speed: float = Query(1.0, ge=0.25, le=4.0),
    current_user: User = Depends(get_current_user),
    ai_client: OpenAIClient = Depends(get_ai_client),
):
    """
    Convert text to speech using OpenAI TTS.

    Returns audio as MP3 bytes.

    Args:
        text: Text to convert (max 4096 characters).
        voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer).
        speed: Playback speed (0.25 to 4.0).
    """
    try:
        audio_bytes = await ai_client.text_to_speech(
            text=text,
            voice=voice,
            speed=speed,
        )

        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": 'inline; filename="jarvis-speech.mp3"',
                "Cache-Control": "no-cache",
            },
        )

    except Exception as e:
        logger.error("TTS failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Text-to-speech failed: {str(e)}",
        )
