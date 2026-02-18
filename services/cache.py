"""
Кеширование пользователей с использованием Redis для поддержки нескольких инстансов.

Кешируется CachedUser (dataclass), а НЕ ORM-объект User, чтобы избежать
DetachedInstanceError при обращении к relationship вне сессии.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import json
import logging
from datetime import datetime, timedelta

from database.models import UserRole
from config import config

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CachedUser:
    """Легковесный снимок пользователя для кеша (не ORM-объект)."""
    id: int
    telegram_id: int
    full_name: str
    role: UserRole
    is_active: bool

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "telegram_id": self.telegram_id,
            "full_name": self.full_name,
            "role": self.role.value,
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, d: dict) -> CachedUser:
        return cls(
            id=d["id"],
            telegram_id=d["telegram_id"],
            full_name=d["full_name"],
            role=UserRole(d["role"]),
            is_active=d["is_active"],
        )

    @classmethod
    def from_orm(cls, user) -> CachedUser:
        """Создать из SQLAlchemy User."""
        return cls(
            id=user.id,
            telegram_id=user.telegram_id,
            full_name=user.full_name,
            role=user.role if isinstance(user.role, UserRole) else UserRole(user.role),
            is_active=user.is_active,
        )


class RedisUserCache:
    """Кеш пользователей на Redis с TTL."""

    def __init__(self, redis_client, ttl_seconds: int = 300):
        self.redis = redis_client
        self.ttl = ttl_seconds
        self._prefix = "user_cache:"

    def _key(self, telegram_id: int) -> str:
        return f"{self._prefix}{telegram_id}"

    async def get(self, telegram_id: int) -> Optional[CachedUser]:
        """Получить кешированного пользователя."""
        try:
            key = self._key(telegram_id)
            data = await self.redis.get(key)
            if data:
                return CachedUser.from_dict(json.loads(data))
        except Exception as e:
            logger.debug("Cache get error for user %s: %s", telegram_id, e)
        return None

    async def set(self, telegram_id: int, user) -> None:
        """Сохранить пользователя в кеш (принимает ORM User или CachedUser)."""
        try:
            key = self._key(telegram_id)
            if isinstance(user, CachedUser):
                cached = user
            else:
                cached = CachedUser.from_orm(user)
            await self.redis.setex(key, self.ttl, json.dumps(cached.to_dict()))
        except Exception as e:
            logger.warning("Cache set error for user %s: %s", telegram_id, e)

    async def invalidate(self, telegram_id: int) -> None:
        try:
            await self.redis.delete(self._key(telegram_id))
        except Exception as e:
            logger.debug("Cache invalidate error for user %s: %s", telegram_id, e)

    async def clear(self) -> None:
        try:
            pattern = f"{self._prefix}*"
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
        except Exception as e:
            logger.warning("Cache clear error: %s", e)


class MemoryUserCache:
    """In-memory кеш пользователей (fallback если Redis недоступен)."""

    def __init__(self, ttl_seconds: int = 300):
        import asyncio
        self._cache: dict[int, tuple[CachedUser, datetime]] = {}
        self._ttl = timedelta(seconds=ttl_seconds)
        self._lock = asyncio.Lock()

    async def get(self, telegram_id: int) -> Optional[CachedUser]:
        async with self._lock:
            if telegram_id in self._cache:
                cached, expiry = self._cache[telegram_id]
                if datetime.now() < expiry:
                    return cached
                del self._cache[telegram_id]
        return None

    async def set(self, telegram_id: int, user) -> None:
        async with self._lock:
            if isinstance(user, CachedUser):
                cached = user
            else:
                cached = CachedUser.from_orm(user)
            self._cache[telegram_id] = (cached, datetime.now() + self._ttl)

    async def invalidate(self, telegram_id: int) -> None:
        async with self._lock:
            self._cache.pop(telegram_id, None)

    async def clear(self) -> None:
        async with self._lock:
            self._cache.clear()


# Глобальный экземпляр кеша (инициализируется в main.py)
user_cache: Optional[RedisUserCache | MemoryUserCache] = None


async def init_cache(redis_client=None) -> RedisUserCache | MemoryUserCache:
    """Инициализировать кеш пользователей."""
    global user_cache
    if redis_client:
        try:
            await redis_client.ping()
            user_cache = RedisUserCache(redis_client, ttl_seconds=config.REDIS_CACHE_TTL)
            logger.info("Using Redis cache for users")
            return user_cache
        except Exception as e:
            logger.warning("Redis not available for cache, using memory: %s", e)

    user_cache = MemoryUserCache(ttl_seconds=config.REDIS_CACHE_TTL)
    logger.info("Using memory cache for users")
    return user_cache
