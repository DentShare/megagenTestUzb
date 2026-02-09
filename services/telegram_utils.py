"""
Утилиты для работы с Telegram API: экранирование Markdown, безопасный edit_text.
"""
import logging
from typing import Optional

from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest

logger = logging.getLogger(__name__)


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
    Безопасный edit_text: ловит TelegramBadRequest (message not modified, not found, parse error).
    Возвращает True при успехе, False при ожидаемых ошибках.
    """
    try:
        await message.edit_text(
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            **kwargs
        )
        return True
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
