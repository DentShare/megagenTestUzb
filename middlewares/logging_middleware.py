"""
Middleware для логирования входящих событий и исключений.

Цели:
- видеть каждый апдейт (message/callback) и кто его отправил
- получать полный traceback и контекст, если упало в любом месте обработчика
"""

import logging
import time
from typing import Callable, Dict, Any, Awaitable, Optional

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery


logger = logging.getLogger(__name__)


def _truncate(text: Optional[str], limit: int = 200) -> Optional[str]:
    if text is None:
        return None
    text = text.replace("\n", "\\n")
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


class LoggingMiddleware(BaseMiddleware):
    """Логирует старт/финиш обработки события + исключения с контекстом."""

    def __init__(self, log_success: bool = True):
        self.log_success = log_success

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        started = time.monotonic()

        event_type = type(event).__name__
        user_id = None
        chat_id = None
        payload = None

        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
            chat_id = event.chat.id if event.chat else None
            payload = _truncate(event.text or event.caption)
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None
            chat_id = event.message.chat.id if event.message and event.message.chat else None
            payload = _truncate(event.data)

        # Корреляционный ID на время обработки одного события
        trace_id = f"{int(time.time() * 1000)}:{user_id or 'na'}"
        data["trace_id"] = trace_id

        logger.info(
            "IN  trace=%s type=%s user=%s chat=%s payload=%s",
            trace_id,
            event_type,
            user_id,
            chat_id,
            payload,
        )

        try:
            result = await handler(event, data)
            ms = (time.monotonic() - started) * 1000
            if self.log_success:
                logger.info(
                    "OUT trace=%s type=%s user=%s chat=%s time_ms=%.1f",
                    trace_id,
                    event_type,
                    user_id,
                    chat_id,
                    ms,
                )
            return result
        except Exception as e:
            ms = (time.monotonic() - started) * 1000
            logger.error(
                "ERR trace=%s type=%s user=%s chat=%s time_ms=%.1f err=%s",
                trace_id,
                event_type,
                user_id,
                chat_id,
                ms,
                repr(e),
                exc_info=True,
            )
            raise

