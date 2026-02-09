"""
Сервис для работы с заказами.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import Order, OrderItem, OrderStatus, DeliveryType, User, Clinic
from services.catalog_stock import get_qty, subtract
from config import config

logger = logging.getLogger(__name__)


class OrderService:
    """Сервис для создания и управления заказами."""
    
    @staticmethod
    async def validate_stock(
        session: AsyncSession,
        cart: List[Dict[str, Any]]
    ) -> tuple[bool, Optional[str]]:
        """
        Проверить наличие товаров на складе.
        
        Args:
            session: Сессия БД
            cart: Список товаров в корзине
            
        Returns:
            (is_valid, error_message)
        """
        if not getattr(config, "USE_CATALOG_STOCK", False):
            return True, None
        
        try:
            from collections import defaultdict
            by_sku = defaultdict(int)
            for item in cart:
                by_sku[item["sku"]] += item["quantity"]
            
            for sku, need in by_sku.items():
                available = get_qty(sku)
                if available < need:
                    name = next((i["name"] for i in cart if i["sku"] == sku), sku)
                    return False, f"Недостаточно на складе: {name}. Доступно: {available} шт."
            
            return True, None
        except Exception as e:
            logger.error(f"Stock validation error: {e}", exc_info=True)
            return False, f"Ошибка проверки остатков: {e}"
    
    @staticmethod
    async def create_order(
        session: AsyncSession,
        manager_id: int,
        clinic_id: int,
        cart: List[Dict[str, Any]],
        is_urgent: bool = False,
        delivery_type: DeliveryType = DeliveryType.COURIER
    ) -> tuple[Optional[Order], Optional[str]]:
        """
        Создать заказ с транзакцией.
        
        Args:
            session: Сессия БД
            manager_id: ID менеджера
            clinic_id: ID клиники
            cart: Список товаров
            is_urgent: Срочный заказ
            delivery_type: Тип доставки
            
        Returns:
            (order, error_message)
        """
        try:
            # Проверяем остатки перед созданием заказа
            is_valid, error = await OrderService.validate_stock(session, cart)
            if not is_valid:
                return None, error
            
            # Сессия из middleware уже в транзакции — не вызываем session.begin()
            new_order = Order(
                manager_id=manager_id,
                clinic_id=clinic_id,
                status=OrderStatus.NEW,
                is_urgent=is_urgent,
                delivery_type=delivery_type
            )
            session.add(new_order)
            await session.flush()  # Получаем ID заказа
            
            # Добавляем товары
            for item in cart:
                order_item = OrderItem(
                    order_id=new_order.id,
                    item_sku=item['sku'],
                    item_name=item['name'],
                    quantity=item['quantity']
                )
                session.add(order_item)
            
            # Вычитаем остатки
            if getattr(config, "USE_CATALOG_STOCK", False):
                for item in cart:
                    if not subtract(item["sku"], item["quantity"]):
                        logger.warning(
                            f"Failed to subtract stock for sku={item['sku']}, qty={item['quantity']}"
                        )
            
            await session.commit()
            await session.refresh(new_order)
            
            logger.info(
                f"Order created: id={new_order.id}, manager={manager_id}, "
                f"clinic={clinic_id}, items={len(cart)}"
            )
            return new_order, None
                
        except Exception as e:
            logger.error(f"Error creating order: {e}", exc_info=True)
            await session.rollback()
            return None, f"Ошибка создания заказа: {e}"
    
    @staticmethod
    async def get_order_with_items(
        session: AsyncSession,
        order_id: int
    ) -> Optional[Order]:
        """
        Получить заказ со всеми товарами.
        
        Args:
            session: Сессия БД
            order_id: ID заказа
            
        Returns:
            Order или None
        """
        from sqlalchemy.orm import selectinload
        stmt = (
            select(Order)
            .options(
                selectinload(Order.items),
                selectinload(Order.clinic),
                selectinload(Order.manager),
                selectinload(Order.courier)
            )
            .where(Order.id == order_id)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_order_status(
        session: AsyncSession,
        order_id: int,
        status: OrderStatus,
        user_id: Optional[int] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Обновить статус заказа.
        
        Args:
            session: Сессия БД
            order_id: ID заказа
            status: Новый статус
            user_id: ID пользователя (для логирования)
            
        Returns:
            (success, error_message)
        """
        try:
            order = await OrderService.get_order_with_items(session, order_id)
            if not order:
                return False, "Заказ не найден"
            
            old_status = order.status
            order.status = status
            
            # Обновляем временные метки
            if status == OrderStatus.ASSEMBLY:
                order.assembled_at = datetime.utcnow()
            elif status == OrderStatus.DELIVERED:
                order.delivered_at = datetime.utcnow()
            
            await session.commit()
            await session.refresh(order)
            
            logger.info(
                f"Order status updated: id={order_id}, {old_status} -> {status}, user={user_id}"
            )
            return True, None
            
        except Exception as e:
            logger.error(f"Error updating order status: {e}", exc_info=True)
            await session.rollback()
            return False, f"Ошибка обновления статуса: {e}"

