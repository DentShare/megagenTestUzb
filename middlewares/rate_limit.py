"""
Rate limiting middleware с поддержкой Redis для multi-instance окружений.
"""
from typing import Callable, Dict, Any, Awaitable, Optional
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
import time
import logging

logger = logging.getLogger(__name__)


class RedisRateLimitMiddleware(BaseMiddleware):
    """Ограничение количества запросов через Redis."""
    
    def __init__(
        self,
        redis_client,
        max_calls: int = 10,
        period: float = 60.0,
        key_prefix: str = "rate_limit:"
    ):
        """
        Args:
            redis_client: Клиент Redis (async)
            max_calls: Максимальное количество запросов за период
            period: Период в секундах
            key_prefix: Префикс для ключей Redis
        """
        self.redis = redis_client
        self.max_calls = max_calls
        self.period = int(period)
        self.key_prefix = key_prefix
    
    def _key(self, user_id: int) -> str:
        """Генерация ключа для Redis."""
        return f"{self.key_prefix}{user_id}"
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None
        
        if not user_id:
            return await handler(event, data)
        
        try:
            key = self._key(user_id)
            # Используем INCR и EXPIRE для атомарной операции
            current = await self.redis.incr(key)
            if current == 1:
                # Первый запрос - устанавливаем TTL
                await self.redis.expire(key, self.period)
            
            if current > self.max_calls:
                # Превышен лимит
                if isinstance(event, CallbackQuery):
                    await event.answer("⚠️ Слишком много запросов. Подождите немного.", show_alert=True)
                elif isinstance(event, Message):
                    await event.answer("⚠️ Слишком много запросов. Подождите немного.")
                return
        
            return await handler(event, data)
        except Exception as e:
            logger.warning("Rate limit error for user %s: %s", user_id, e)
            # При ошибке Redis пропускаем запрос
            return await handler(event, data)


class MemoryRateLimitMiddleware(BaseMiddleware):
    """In-memory rate limiting (fallback)."""
    
    def __init__(self, max_calls: int = 10, period: float = 60.0):
        """
        Args:
            max_calls: Максимальное количество запросов за период
            period: Период в секундах
        """
        self.max_calls = max_calls
        self.period = period
        from collections import defaultdict
        self.calls = defaultdict(list)
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None
        
        if not user_id:
            return await handler(event, data)
        
        now = time.time()
        user_calls = self.calls[user_id]
        # Удаляем старые записи
        user_calls[:] = [t for t in user_calls if now - t < self.period]
        
        if len(user_calls) >= self.max_calls:
            if isinstance(event, CallbackQuery):
                await event.answer("⚠️ Слишком много запросов. Подождите немного.", show_alert=True)
            elif isinstance(event, Message):
                await event.answer("⚠️ Слишком много запросов. Подождите немного.")
            return
        
        user_calls.append(now)
        return await handler(event, data)


async def create_rate_limit_middleware(
    redis_client=None,
    max_calls: int = 10,
    period: float = 60.0
) -> RedisRateLimitMiddleware | MemoryRateLimitMiddleware:
    """
    Создать middleware для rate limiting.
    
    Args:
        redis_client: Клиент Redis (опционально)
        max_calls: Максимальное количество запросов
        period: Период в секундах
        
    Returns:
        Экземпляр middleware (Redis или Memory)
    """
    if redis_client:
        try:
            await redis_client.ping()
            return RedisRateLimitMiddleware(redis_client, max_calls, period)
        except Exception as e:
            logger.warning("Redis not available for rate limiting, using memory: %s", e)
    
    return MemoryRateLimitMiddleware(max_calls, period)
