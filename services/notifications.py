"""
Сервис для отправки уведомлений менеджерам о изменении статуса заказов.
"""
import logging
from typing import Optional
from aiogram import Bot

from services.telegram_utils import escape_markdown
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from database.models import Order, OrderStatus, User

logger = logging.getLogger(__name__)


async def notify_manager_about_order_status(
    bot: Bot,
    order: Order,
    old_status: OrderStatus,
    new_status: OrderStatus,
    session: AsyncSession
) -> bool:
    """
    Уведомить менеджера об изменении статуса заказа.
    Включая уведомление о доставке (DELIVERED).
    
    Args:
        bot: Экземпляр бота
        order: Заказ
        old_status: Старый статус
        new_status: Новый статус
        session: Сессия БД
        
    Returns:
        True если уведомление отправлено успешно, False в противном случае
    """
    # Не уведомляем только при отмене
    if new_status == OrderStatus.CANCELED:
        return False
    
    # Загружаем менеджера если еще не загружен
    if not order.manager:
        stmt = select(User).where(User.id == order.manager_id)
        result = await session.execute(stmt)
        order.manager = result.scalar_one_or_none()
    
    if not order.manager:
        logger.warning(f"Manager not found for order {order.id}")
        return False
    
    # Формируем текст уведомления
    status_names = {
        OrderStatus.NEW: "Новый",
        OrderStatus.ASSEMBLY: "В сборке",
        OrderStatus.READY_FOR_PICKUP: "Готов к выдаче",
        OrderStatus.DELIVERING: "В доставке",
        OrderStatus.DELIVERED: "Доставлен",
        OrderStatus.CANCELED: "Отменен"
    }
    
    old_status_name = status_names.get(old_status, old_status.value)
    new_status_name = status_names.get(new_status, new_status.value)
    
    # Загружаем клинику если нужно
    if not order.clinic:
        from services.db_ops import get_clinic_by_id
        order.clinic = await get_clinic_by_id(session, order.clinic_id)
    
    clinic_name = escape_markdown(order.clinic.name if order.clinic else "Неизвестная клиника")

    notification_text = (
        f"📦 *Обновление статуса заказа*\n\n"
        f"Заказ: #{order.id}\n"
        f"Клиника: {clinic_name}\n"
        f"Статус: {old_status_name} → {new_status_name}\n"
    )
    
    if order.is_urgent:
        notification_text += "\n🔥 *СРОЧНЫЙ ЗАКАЗ*"
    
    # Отправляем уведомление
    try:
        await bot.send_message(
            chat_id=order.manager.telegram_id,
            text=notification_text,
            parse_mode="Markdown"
        )
        logger.info(
            f"Manager {order.manager.telegram_id} notified about order {order.id} "
            f"status change: {old_status} -> {new_status}"
        )
        return True
    except Exception as e:
        logger.error(
            f"Failed to notify manager {order.manager.telegram_id} about order {order.id}: {e}",
            exc_info=True
        )
        return False

