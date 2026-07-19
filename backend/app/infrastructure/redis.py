"""
Redis Client

Provides async Redis connection for caching, session storage,
and real-time pub/sub messaging.
"""

import redis.asyncio as aioredis
from app.config import settings

redis_client = aioredis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True,
    max_connections=20,
)

# Channel names for pub/sub
REDIS_CHANNEL_CHAT = "jarvis:chat:stream"
REDIS_CHANNEL_NOTIFICATIONS = "jarvis:notifications"
REDIS_CHANNEL_TASKS = "jarvis:tasks"
