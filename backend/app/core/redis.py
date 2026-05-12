import redis.asyncio as redis

from app.core.config import settings

_redis_client = None


def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


# Backward compatibility — still importable as `redis_client` but lazily evaluated
class _LazyRedis:
    """Proxy that creates the real client on first attribute access."""
    def __getattr__(self, name):
        return getattr(get_redis_client(), name)


redis_client = _LazyRedis()
