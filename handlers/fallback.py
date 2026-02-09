"""
Обработчик необработанных обновлений.
Подключается последним — ловит сообщения и callback, которые не попали в другие хендлеры.
"""
import logging
from aiogram import Router, types

logger = logging.getLogger(__name__)
router = Router()


@router.message()
async def fallback_message(message: types.Message):
    """Любое текстовое сообщение, не обработанное другими хендлерами."""
    await message.answer("Используйте /start для начала работы или меню ниже.")


@router.callback_query()
async def fallback_callback(callback: types.CallbackQuery):
    """Любой callback, не обработанный другими хендлерами (устаревшие кнопки и т.п.)."""
    try:
        await callback.answer("Действие устарело. Отправьте /start для обновления меню.")
    except Exception:
        pass
