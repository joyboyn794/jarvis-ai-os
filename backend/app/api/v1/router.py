"""
API v1 Router

Aggregates all v1 route modules into a single router.
"""

from fastapi import APIRouter

from app.api.v1 import auth, chat, memory, voice

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(chat.router)
api_router.include_router(memory.router)
api_router.include_router(voice.router)
