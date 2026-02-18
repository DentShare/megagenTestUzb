"""
Middleware для dependency injection сессий БД.
"""
import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import OperationalError
from database.core import session_maker

logger = logging.getLogger(__name__)


class DatabaseMiddleware(BaseMiddleware):
    """Middleware для автоматического создания и закрытия сессий БД."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        try:
            async with session_maker() as session:
                data['session'] = session
                return await handler(event, data)
        except (OperationalError, ConnectionRefusedError, OSError) as e:
            logger.error("Database connection error: %s", e, exc_info=True)
            error_message = "❌ Ошибка подключения к базе данных. Попробуйте позже."

            if isinstance(event, CallbackQuery):
                try:
                    await event.answer(error_message, show_alert=True)
                except Exception:
                    pass
            elif isinstance(event, Message):
                try:
                    await event.answer(error_message)
                except Exception:
                    pass
            return

