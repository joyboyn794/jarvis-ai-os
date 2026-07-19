"""
Redis Client (Optional)

Provides async Redis connection for caching, session storage,
and real-time pub/sub messaging.

Redis is only initialized when USE_REDIS=true in settings.
"""

# Channel names for pub/sub (used even without Redis connection)
REDIS_CHANNEL_CHAT = "jarvis:chat:stream"
REDIS_CHANNEL_NOTIFICATIONS = "jarvis:notifications"
REDIS_CHANNEL_TASKS = "jarvis:tasks"


class _NoRedis:
    """Fallback when Redis is disabled."""

    async def ping(self):
        raise ConnectionError("Redis is disabled")

    async def close(self):
        pass

    async def get(self, key: str):
        return None

    async def set(self, key: str, value: str, ex: int = None):
        pass

    async def delete(self, key: str):
        pass

    async def publish(self, channel: str, message: str):
        pass


redis_client = _NoRedis()


def init_redis():
    """Initialize Redis connection. Call this when USE_REDIS is enabled."""
    global redis_client
    import redis.asyncio as aioredis
    from app.config import settings

    redis_client = aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        max_connections=20,
    )
    return redis_client
