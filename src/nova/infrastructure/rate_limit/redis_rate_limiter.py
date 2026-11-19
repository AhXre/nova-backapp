from redis.asyncio import Redis

from nova.application.ports.rate_limit import RateLimiter


class RedisRateLimiter(RateLimiter):
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        current = await self._redis.incr(key)
        if current == 1:
            await self._redis.expire(key, window_seconds)
        return current <= limit
