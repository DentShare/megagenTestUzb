"""
Кеширование пользователей с использованием Redis для поддержки нескольких инстансов.
"""
from typing import Optional
import json
import logging
from datetime import timedelta
from database.models import User
from config import config

logger = logging.getLogger(__name__)


class RedisUserCache:
    """Кеш пользователей на Redis с TTL."""
    
    def __init__(self, redis_client, ttl_seconds: int = 300):
        """
        Args:
            redis_client: Клиент Redis (async)
            ttl_seconds: TTL в секундах
        """
        self.redis = redis_client
        self.ttl = ttl_seconds
        self._prefix = "user_cache:"
    
    def _key(self, telegram_id: int) -> str:
        """Генерация ключа для Redis."""
        return f"{self._prefix}{telegram_id}"
    
    async def get(self, telegram_id: int) -> Optional[User]:
        """
        Получить пользователя из кеша.
        
        Args:
            telegram_id: Telegram ID пользователя
            
        Returns:
            User или None если не найден
        """
        try:
            key = self._key(telegram_id)
            data = await self.redis.get(key)
            if data:
                # Декодируем из JSON
                user_data = json.loads(data)
                # Создаем объект User из словаря
                # Внимание: это упрощенная версия, в реальности нужно использовать SQLAlchemy
                from database.models import UserRole
                user = User(
                    id=user_data["id"],
                    telegram_id=user_data["telegram_id"],
                    full_name=user_data["full_name"],
                    role=UserRole(user_data["role"]),
                    is_active=user_data["is_active"]
                )
                return user
        except Exception as e:
            logger.debug(f"Cache get error for user {telegram_id}: {e}")
        return None
    
    async def set(self, telegram_id: int, user: User):
        """
        Сохранить пользователя в кеш.
        
        Args:
            telegram_id: Telegram ID пользователя
            user: Объект User
        """
        try:
            key = self._key(telegram_id)
            # Сериализуем в JSON
            user_data = {
                "id": user.id,
                "telegram_id": user.telegram_id,
                "full_name": user.full_name,
                "role": user.role.value if hasattr(user.role, "value") else str(user.role),
                "is_active": user.is_active
            }
            data = json.dumps(user_data)
            await self.redis.setex(key, self.ttl, data)
        except Exception as e:
            logger.warning(f"Cache set error for user {telegram_id}: {e}")
    
    async def invalidate(self, telegram_id: int):
        """
        Удалить пользователя из кеша.
        
        Args:
            telegram_id: Telegram ID пользователя
        """
        try:
            key = self._key(telegram_id)
            await self.redis.delete(key)
        except Exception as e:
            logger.debug(f"Cache invalidate error for user {telegram_id}: {e}")
    
    async def clear(self):
        """Очистить весь кеш пользователей."""
        try:
            pattern = f"{self._prefix}*"
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
        except Exception as e:
            logger.warning(f"Cache clear error: {e}")


class MemoryUserCache:
    """In-memory кеш пользователей (fallback если Redis недоступен)."""
    
    def __init__(self, ttl_seconds: int = 300):
        import asyncio
        from datetime import datetime, timedelta
        self._cache: dict[int, tuple] = {}  # telegram_id -> (user, expiry)
        self._ttl = timedelta(seconds=ttl_seconds)
        self._lock = asyncio.Lock()
    
    async def get(self, telegram_id: int) -> Optional[User]:
        """Получить пользователя из кеша."""
        from datetime import datetime
        async with self._lock:
            if telegram_id in self._cache:
                user, expiry = self._cache[telegram_id]
                if datetime.now() < expiry:
                    return user
                del self._cache[telegram_id]
        return None
    
    async def set(self, telegram_id: int, user: User):
        """Сохранить пользователя в кеш."""
        from datetime import datetime
        async with self._lock:
            self._cache[telegram_id] = (user, datetime.now() + self._ttl)
    
    async def invalidate(self, telegram_id: int):
        """Удалить пользователя из кеша."""
        async with self._lock:
            self._cache.pop(telegram_id, None)
    
    async def clear(self):
        """Очистить весь кеш."""
        async with self._lock:
            self._cache.clear()


# Глобальный экземпляр кеша (инициализируется в main.py)
user_cache: Optional[RedisUserCache | MemoryUserCache] = None


async def init_cache(redis_client=None) -> RedisUserCache | MemoryUserCache:
    """
    Инициализировать кеш пользователей.
    
    Args:
        redis_client: Клиент Redis (опционально)
        
    Returns:
        Экземпляр кеша (Redis или Memory)
    """
    global user_cache
    if redis_client:
        try:
            await redis_client.ping()
            user_cache = RedisUserCache(redis_client, ttl_seconds=config.REDIS_CACHE_TTL)
            logger.info("Using Redis cache for users")
            return user_cache
        except Exception as e:
            logger.warning(f"Redis not available for cache, using memory: {e}")
    
    user_cache = MemoryUserCache(ttl_seconds=config.REDIS_CACHE_TTL)
    logger.info("Using memory cache for users")
    return user_cache
