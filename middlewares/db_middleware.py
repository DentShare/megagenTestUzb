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
                try:
                    return await handler(event, data)
                finally:
                    await session.close()
        except (OperationalError, ConnectionRefusedError, OSError) as e:
            # Важно: пишем traceback, чтобы было видно где именно упало
            logger.error(f"Database connection error: {e}", exc_info=True)
            error_message = "❌ Ошибка подключения к базе данных. Попробуйте позже."
            
            if isinstance(event, CallbackQuery):
                try:
                    await event.answer(error_message, show_alert=True)
                except:
                    pass
            elif isinstance(event, Message):
                try:
                    await event.answer(error_message)
                except:
                    pass
            return

