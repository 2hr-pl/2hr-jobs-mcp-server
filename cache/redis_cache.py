import json
import hashlib
import redis.asyncio as aioredis
import os
from typing import Optional, Any


class RedisCache:

    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._client: Optional[aioredis.Redis] = None

    async def get_client(self) -> aioredis.Redis:
        if self._client is None:
            self._client = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._client

    def _make_key(self, prefix: str, params: dict) -> str:
        params_hash = hashlib.md5(
            json.dumps(params, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        return f"mcp:{prefix}:{params_hash}"

    async def get(self, key: str) -> Optional[Any]:
        try:
            client = await self.get_client()
            value = await client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception:
            return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        try:
            client = await self.get_client()
            await client.setex(key, ttl, json.dumps(value, ensure_ascii=False))
        except Exception:
            pass

    async def get_or_set(self, prefix: str, params: dict, fetch_fn, ttl: int = 300) -> Any:
        key = self._make_key(prefix, params)
        cached = await self.get(key)
        if cached is not None:
            return {**cached, "_cached": True}
        result = await fetch_fn()
        await self.set(key, result, ttl)
        return {**result, "_cached": False}

    async def invalidate(self, prefix: str) -> int:
        try:
            client = await self.get_client()
            keys = await client.keys(f"mcp:{prefix}:*")
            if keys:
                return await client.delete(*keys)
            return 0
        except Exception:
            return 0


_cache: Optional[RedisCache] = None


def get_cache() -> RedisCache:
    global _cache
    if _cache is None:
        _cache = RedisCache()
    return _cache
