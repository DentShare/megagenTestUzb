import logging
from datetime import datetime, timezone
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, UserRole, Order, OrderStatus, DeliveryType, Clinic, OrderItem
from config import config
from services.db_ops import get_user_by_telegram_id, check_role
from services.telegram_utils import escape_markdown, safe_edit_text
from services.printer import generate_label, generate_collected_label, send_to_printer
from keyboards.warehouse_kbs import get_warehouse_order_kb, get_warehouse_orders_list_kb, get_warehouse_order_detail_kb
from states.warehouse_states import WarehouseState

logger = logging.getLogger(__name__)

router = Router()

async def is_warehouse(user_id: int, session: AsyncSession) -> bool:
    """Проверка прав склада (делегирует в единую check_role)."""
    return await check_role(session, user_id, UserRole.WAREHOUSE)


async def _get_active_orders(session: AsyncSession):
    """Получить активные заказы (NEW/ASSEMBLY) со всеми связями."""
    stmt = (
        select(Order)
        .options(
            selectinload(Order.clinic),
            selectinload(Order.manager),
            selectinload(Order.items)
        )
        .where(Order.status.in_([OrderStatus.NEW, OrderStatus.ASSEMBLY]))
        .order_by(Order.is_urgent.desc(), Order.created_at.asc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def _get_order_detail(session: AsyncSession, order_id: int) -> Order | None:
    """Получить заказ по ID со всеми связями."""
    stmt = (
        select(Order)
        .options(
            selectinload(Order.clinic),
            selectinload(Order.manager),
            selectinload(Order.items)
        )
        .where(Order.id == order_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


@router.callback_query(F.data == "warehouse:orders")
async def warehouse_menu_orders(callback: types.CallbackQuery, session: AsyncSession):
    """Показать список активных заказов в виде кнопок"""
    if not await is_warehouse(callback.from_user.id, session):
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    orders = await _get_active_orders(session)

    if not orders:
        await callback.message.edit_text("Нет активных заказов.")
        return

    await callback.message.edit_text(
        f"📦 Активные заказы: {len(orders)}\n\nВыберите заказ:",
        reply_markup=get_warehouse_orders_list_kb(orders)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("warehouse:order:"))
async def warehouse_order_detail(callback: types.CallbackQuery, session: AsyncSession):
    """Показать детали заказа по нажатию на кнопку"""
    if not await is_warehouse(callback.from_user.id, session):
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    order_id = int(callback.data.split(":")[-1])
    order = await _get_order_detail(session, order_id)
    
    if not order or order.status not in [OrderStatus.NEW, OrderStatus.ASSEMBLY]:
        await callback.answer("Заказ не найден или уже обработан", show_alert=True)
        return

    icon = "🔥" if order.is_urgent else "🟢"
    status_map = {OrderStatus.NEW: "Новый", OrderStatus.ASSEMBLY: "В сборке"}
    manager_name = escape_markdown(order.manager.full_name if order.manager else "Неизвестен")
    doctor_name = escape_markdown(order.clinic.doctor_name if order.clinic else "—")
    clinic_name = escape_markdown(order.clinic.name if order.clinic else "—")
    created_date = order.created_at.strftime("%d.%m.%Y %H:%M") if order.created_at else "—"
    
    text = (
        f"{icon} *Заказ #{order.id}*\n\n"
        f"👤 *Врач:* {doctor_name}\n"
        f"👤 *Менеджер:* {manager_name}\n"
        f"🏥 *Клиника:* {clinic_name}\n"
        f"📅 *Создан:* {created_date}\n"
        f"📊 *Статус:* {status_map.get(order.status, order.status.value)}\n"
        f"🚚 *Доставка:* {order.delivery_type.value}\n\n"
        f"📦 *Товары:*\n"
    )
    if order.items:
        for idx, item in enumerate(order.items, 1):
            name = (item.replacement_name or item.item_name) if getattr(item, "replacement_name", None) else item.item_name
            if getattr(item, "need_replacement", False) and not getattr(item, "replacement_sku", None):
                text += f"{idx}. {escape_markdown(name)} — {item.quantity} шт. _⏳ ждёт замену_\n"
            else:
                text += f"{idx}. {escape_markdown(name)} — {item.quantity} шт.\n"
    else:
        text += "⚠️ Товары не найдены\n"

    await safe_edit_text(
        callback.message,
        text,
        reply_markup=get_warehouse_order_detail_kb(order.id, order.status.value, order.items),
    )
    await callback.answer()

@router.message(Command("warehouse"))
async def cmd_warehouse(message: types.Message, session: AsyncSession):
    if not await is_warehouse(message.from_user.id, session):
        return

    orders = await _get_active_orders(session)

    if not orders:
        await message.answer("Нет активных заказов.")
        return

    await message.answer(
        f"📦 Активные заказы: {len(orders)}\n\nВыберите заказ:",
        reply_markup=get_warehouse_orders_list_kb(orders)
    )

# --- Actions ---

@router.callback_query(F.data.startswith("wh_item_out:"))
async def mark_item_out_of_stock(callback: types.CallbackQuery, session: AsyncSession):
    """Склад отмечает товар как «нет в наличии»; менеджер сможет подобрать замену."""
    if not await is_warehouse(callback.from_user.id, session):
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Ошибка", show_alert=True)
        return
    order_id = int(parts[1])
    item_id = int(parts[2])
    stmt = select(OrderItem).where(
        OrderItem.id == item_id,
        OrderItem.order_id == order_id
    )
    result = await session.execute(stmt)
    item = result.scalar_one_or_none()
    if not item:
        await callback.answer("Товар не найден", show_alert=True)
        return
    if getattr(item, "need_replacement", False):
        await callback.answer("Уже отмечено как нет в наличии", show_alert=True)
        return
    item.need_replacement = True
    await session.commit()
    # Уведомить менеджера и обновить экран (один запрос вместо двух)
    order = await _get_order_detail(session, order_id)
    if order and order.manager and order.manager.telegram_id:
        try:
            await callback.bot.send_message(
                order.manager.telegram_id,
                f"📦 *Заказ #{order.id}*\n\n"
                f"Склад указал: *нет в наличии* — {escape_markdown(item.item_name)} ({item.quantity} шт.).\n\n"
                "Подберите замену в разделе *🔄 Замены* в меню менеджера.",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error("Notify manager about out-of-stock: %s", e)
    await callback.answer("Отмечено. Менеджер получит уведомление о замене.")
    if order and order.status in [OrderStatus.NEW, OrderStatus.ASSEMBLY]:
        icon = "🔥" if order.is_urgent else "🟢"
        status_map = {OrderStatus.NEW: "Новый", OrderStatus.ASSEMBLY: "В сборке"}
        manager_name = escape_markdown(order.manager.full_name if order.manager else "Неизвестен")
        doctor_name = escape_markdown(order.clinic.doctor_name if order.clinic else "—")
        clinic_name = escape_markdown(order.clinic.name if order.clinic else "—")
        created_date = order.created_at.strftime("%d.%m.%Y %H:%M") if order.created_at else "—"
        text = (
            f"{icon} *Заказ #{order.id}*\n\n"
            f"👤 *Врач:* {doctor_name}\n"
            f"👤 *Менеджер:* {manager_name}\n"
            f"🏥 *Клиника:* {clinic_name}\n"
            f"📅 *Создан:* {created_date}\n"
            f"📊 *Статус:* {status_map.get(order.status, order.status.value)}\n"
            f"🚚 *Доставка:* {order.delivery_type.value}\n\n"
            f"📦 *Товары:*\n"
        )
        for idx, it in enumerate(order.items, 1):
            name = (it.replacement_name or it.item_name) if getattr(it, "replacement_name", None) else it.item_name
            if getattr(it, "need_replacement", False) and not getattr(it, "replacement_sku", None):
                text += f"{idx}. {escape_markdown(name)} — {it.quantity} шт. _⏳ ждёт замену_\n"
            else:
                text += f"{idx}. {escape_markdown(name)} — {it.quantity} шт.\n"
        await callback.message.edit_text(
            text,
            reply_markup=get_warehouse_order_detail_kb(order.id, order.status.value, order.items),
            parse_mode="Markdown"
        )

@router.callback_query(F.data.startswith("wh_take:"))
async def take_order(callback: types.CallbackQuery, session: AsyncSession):
    order_id = int(callback.data.split(":")[1])
    
    stmt = select(Order).options(
        selectinload(Order.manager),
        selectinload(Order.clinic),
        selectinload(Order.items),
    ).where(Order.id == order_id)
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()
    
    if order and order.status == OrderStatus.NEW:
        old_status = order.status
        order.status = OrderStatus.ASSEMBLY
        # Сохраняем items до commit — после commit ленивый доступ к order.items вызовет MissingGreenlet в async
        items_snapshot = list(order.items)
        await session.commit()
        from services.notifications import notify_manager_about_order_status
        await notify_manager_about_order_status(
            callback.bot, order, old_status, OrderStatus.ASSEMBLY, session
        )
        
        await callback.message.edit_reply_markup(reply_markup=get_warehouse_order_detail_kb(order.id, "assembly", items_snapshot))
        await callback.answer("Взято в работу")
    else:
        await callback.answer("Заказ не найден или статус изменен", show_alert=True)

@router.callback_query(F.data.startswith("wh_ready:"))
async def ready_order(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    order_id = int(callback.data.split(":")[1])
    stmt = select(Order).options(
        selectinload(Order.clinic),
        selectinload(Order.manager),
        selectinload(Order.items)
    ).where(Order.id == order_id)
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()
    
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    
    if order.status != OrderStatus.ASSEMBLY:
        await callback.answer("Заказ не в статусе 'В сборке'. Сначала возьмите заказ в работу.", show_alert=True)
        return

    # Данные для QR1 — товары в заказе (с учётом замен: если подобрана замена — печатаем её)
    items_data = [
        {
            "name": (item.replacement_name or item.item_name) if getattr(item, "replacement_name", None) else item.item_name,
            "qty": item.quantity
        }
        for item in order.items
    ]
    manager_name = escape_markdown(order.manager.full_name if order.manager else "Неизвестен")
    doctor_name = escape_markdown(order.clinic.doctor_name if order.clinic else "—")
    clinic_name = escape_markdown(order.clinic.name if order.clinic else "—")
    # QR2: ссылка на Яндекс Навигатор для построения маршрута до клиники
    if order.clinic and (order.clinic.navigator_link or "").startswith("yandexnavi://"):
        navigator_link = order.clinic.navigator_link
    elif order.clinic:
        # Формат: построить маршрут от текущей геолокации до клиники
        navigator_link = f"yandexnavi://build_route_on_map?lat_to={order.clinic.geo_lat}&lon_to={order.clinic.geo_lon}"
    else:
        navigator_link = ""

    # Генерируем этикетку с 2 QR-кодами: товары + навигация
    label_buf = generate_collected_label(
        order_id=order.id,
        doctor_name=doctor_name,
        manager_name=manager_name,
        clinic_name=clinic_name,
        items_data=items_data,
        navigator_link=navigator_link,
        is_urgent=order.is_urgent
    )
    
    # Отправляем в Telegram
    label_buf.seek(0)
    caption = (
        f"📦 *Заказ #{order.id} собран*\n\n"
        f"👤 Врач: {doctor_name}\n"
        f"👤 Менеджер: {manager_name}\n"
        f"🏥 Клиника: {clinic_name}\n\n"
        f"QR1: список товаров (текст)\n"
        f"QR2: Яндекс Навигатор — маршрут до клиники"
    )
    await callback.message.answer_photo(
        photo=types.BufferedInputFile(label_buf.read(), filename="collected_label.png"),
        caption=caption,
        parse_mode="Markdown"
    )
    
    # Печать на принтер
    label_buf.seek(0)
    print_success, print_message = await send_to_printer(label_buf, order.id)
    if print_success:
        await callback.message.answer(f"✅ {print_message}")
    elif print_message and "отключен" not in print_message.lower() and "не указан" not in print_message.lower():
        # Показываем ошибку только если это не просто отключенный принтер
        await callback.message.answer(f"⚠️ Не удалось отправить на принтер: {print_message}")
    
    # 2. Update assembled_at timestamp to NOW (use datetime, not func.now())
    order.assembled_at = datetime.now(timezone.utc)
    
    if order.delivery_type == DeliveryType.COURIER:
        old_status = order.status
        order.status = OrderStatus.READY_FOR_PICKUP
        await session.commit()
        await callback.message.answer("Статус обновлен: Готов к выдаче (Курьер).")
        
        # Уведомляем менеджера
        from services.notifications import notify_manager_about_order_status
        await notify_manager_about_order_status(
            callback.bot, order, old_status, OrderStatus.READY_FOR_PICKUP, session
        )
        
        # Notify all active couriers
        await notify_couriers_about_order(callback.bot, order, session)
        
    elif order.delivery_type == DeliveryType.TAXI:
        # Ask for tracking link
        await state.update_data(current_order_id=order.id)
        await callback.message.answer(f"🚕 Доставка Такси. Пришлите ссылку на трекинг для заказа #{order_id}:")
        await state.set_state(WarehouseState.waiting_for_taxi_link)
        await session.commit()
    
    await callback.answer()

@router.message(WarehouseState.waiting_for_taxi_link)
async def process_taxi_link(message: types.Message, state: FSMContext, session: AsyncSession):
    link = message.text
    data = await state.get_data()
    order_id = data.get('current_order_id')
    stmt = select(Order).options(selectinload(Order.clinic), selectinload(Order.manager)).where(Order.id == order_id)
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()
    
    if order:
        old_status = order.status
        order.status = OrderStatus.DELIVERED
        order.delivered_at = datetime.now(timezone.utc)
        order.taxi_link = link
        await session.commit()
        
        from services.notifications import notify_manager_about_order_status
        await notify_manager_about_order_status(
            message.bot, order, old_status, OrderStatus.DELIVERED, session
        )
        
        # Notify Logic
        chat_id = order.clinic.telegram_chat_id
        if chat_id:
            try:
                await message.bot.send_message(chat_id, f"🚕 Ваш заказ #{order.id} едет к вам!\nСсылка: {link}")
                await message.answer("Врач уведомлен.")
            except Exception as e:
                logger.error("Failed to notify doctor %s for order %s: %s", chat_id, order.id, e)
                await message.answer(f"Не удалось уведомить врача ({e}).")
        
        # Additional logic: if doctor notification fails or not exists?
        # Prompt: "If ID exists -> Send to Doctor. If ID null -> Send to Manager"
        if not chat_id:
            manager_id = order.manager.telegram_id
            try:
                await message.bot.send_message(manager_id, f"🚕 Заказ #{order.id} отправлен на такси.\nПерешлите ссылку врачу: {link}")
                await message.answer("Менеджер уведомлен (у врача нет ID).")
            except Exception as e:
                logger.error("Failed to notify manager %s for order %s: %s", manager_id, order.id, e)
    
    await message.answer(f"✅ Заказ #{order_id} закрыт (Delivered).")
    await state.clear()


async def notify_couriers_about_order(bot, order: Order, session: AsyncSession):
    """Notify all active couriers about a new order ready for pickup"""
    stmt = select(User).where(
        User.role == UserRole.COURIER,
        User.is_active == True
    )
    result = await session.execute(stmt)
    couriers = result.scalars().all()
    
    clinic_name = escape_markdown(order.clinic.name if order.clinic else "—")
    clinic_addr = escape_markdown(order.clinic.address if order.clinic else "—")
    notification_text = (
        f"📦 *Новый заказ готов к доставке!*\n\n"
        f"Заказ: #{order.id}\n"
        f"Клиника: {clinic_name}\n"
        f"Адрес: {clinic_addr}\n"
        f"{'🔥 СРОЧНО' if order.is_urgent else ''}"
    )
    
    notified_count = 0
    for courier in couriers:
        try:
            await bot.send_message(
                courier.telegram_id,
                notification_text,
                parse_mode="Markdown"
            )
            notified_count += 1
        except Exception as e:
            logger.error("Failed to notify courier %s: %s", courier.telegram_id, e)
    
    logger.info("Notified %s/%s couriers about order #%s", notified_count, len(couriers), order.id)
