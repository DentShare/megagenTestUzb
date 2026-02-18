"""
Утилиты для работы с Telegram API: экранирование Markdown, безопасный edit_text.
"""
import asyncio
import logging
from typing import Optional

from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError, TelegramRetryAfter

logger = logging.getLogger(__name__)

# Сетевые ошибки, при которых имеет смысл повторить запрос
RETRYABLE_EXC = (TelegramNetworkError, TelegramRetryAfter)
MAX_EDIT_RETRIES = 3
RETRY_DELAY = 1.0


def escape_markdown(s: str) -> str:
    """
    Экранирует спецсимволы Markdown в пользовательском тексте.
    Использовать для всех полей из БД (имена, названия клиник, товары).
    """
    if not s or not isinstance(s, str):
        return str(s) if s is not None else ""
    # Сначала \ — иначе двойное экранирование сломается
    s = s.replace("\\", "\\\\")
    for ch in "_*[]()`":
        s = s.replace(ch, f"\\{ch}")
    return s


async def safe_edit_text(
    message: Message,
    text: str,
    *,
    reply_markup=None,
    parse_mode: Optional[str] = "Markdown",
    **kwargs
) -> bool:
    """
    Безопасный edit_text: ловит TelegramBadRequest (message not modified, not found, parse error),
    при сетевых ошибках (ServerDisconnected, RetryAfter) повторяет запрос до MAX_EDIT_RETRIES раз.
    Возвращает True при успехе, False при ожидаемых ошибках.
    """
    last_exc = None
    for attempt in range(MAX_EDIT_RETRIES):
        try:
            await message.edit_text(
                text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
                **kwargs
            )
            return True
        except RETRYABLE_EXC as e:
            last_exc = e
            wait = getattr(e, "retry_after", None)
            if wait is None:
                wait = RETRY_DELAY
            if attempt < MAX_EDIT_RETRIES - 1:
                logger.warning("safe_edit_text: %s, retry in %.1fs (attempt %s/%s)", e, wait, attempt + 1, MAX_EDIT_RETRIES)
                await asyncio.sleep(wait)
            else:
                logger.error("safe_edit_text: failed after %s attempts: %s", MAX_EDIT_RETRIES, e)
                raise
        except TelegramBadRequest as e:
            msg = str(e).lower()
            if "message is not modified" in msg or "message to edit not found" in msg:
                logger.debug("safe_edit_text: %s", e)
                return False
            if "can't parse entities" in msg or "can't find end of the entity" in msg:
                logger.warning("safe_edit_text: Markdown parse error, retrying without parse_mode: %s", e)
                try:
                    await message.edit_text(text, reply_markup=reply_markup, **kwargs)
                    return True
                except TelegramBadRequest as e2:
                    logger.warning("safe_edit_text: fallback failed: %s", e2)
                    return False
            raise
    if last_exc:
        raise last_exc
    return False
