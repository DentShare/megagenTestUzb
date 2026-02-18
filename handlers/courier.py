from datetime import datetime, timezone
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, UserRole, Order, OrderStatus, DeliveryType, Clinic
from config import config
from services.db_ops import get_user_by_telegram_id, check_role
from services.routing import (
    optimize_route_with_clusters,
    generate_yandex_maps_url,
    haversine_distance,
)
from keyboards.courier_kbs import (
    get_courier_reply_kb, get_route_action_kb, get_delivery_kb,
    get_single_orders_kb, get_combined_delivery_kb, get_courier_select_orders_kb,
)
from states.courier_states import CourierState

# Maximum radius for order pickup (in kilometers)
MAX_RADIUS_KM = 50

router = Router()

async def is_courier(user_id: int, session: AsyncSession) -> bool:
    """Проверка прав курьера (делегирует в единую check_role)."""
    return await check_role(session, user_id, UserRole.COURIER)

@router.callback_query(F.data == "courier:select_orders")
async def courier_select_orders(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    """Показать список заказов готовых к выдаче — курьер выбирает, какие доставит."""
    if not await is_courier(callback.from_user.id, session):
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    stmt = (
        select(Order)
        .options(selectinload(Order.clinic))
        .where(
            Order.status == OrderStatus.READY_FOR_PICKUP,
            Order.delivery_type == DeliveryType.COURIER
        )
        .order_by(Order.is_urgent.desc(), Order.created_at.asc())
    )
    result = await session.execute(stmt)
    orders = result.scalars().all()
    if not orders:
        await callback.message.edit_text(
            "Нет заказов, готовых к выдаче (курьерская доставка).",
            reply_markup=None
        )
        await callback.answer()
        return
    await state.update_data(selected_order_ids=[])
    await state.set_state(CourierState.selecting_orders)
    text = (
        "📦 *Выберите заказы для доставки*\n\n"
        "Нажмите на заказ, чтобы добавить или убрать из маршрута. "
        "Затем нажмите «Построить маршрут» и отправьте геолокацию."
    )
    await callback.message.edit_text(
        text,
        reply_markup=get_courier_select_orders_kb(orders, []),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("courier:toggle_order:"), CourierState.selecting_orders)
async def courier_toggle_order(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    """Добавить или убрать заказ из выбранных."""
    if not await is_courier(callback.from_user.id, session):
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    try:
        order_id = int(callback.data.split(":")[-1])
    except (ValueError, IndexError):
        await callback.answer("Ошибка", show_alert=True)
        return
    data = await state.get_data()
    selected = list(data.get("selected_order_ids") or [])
    if order_id in selected:
        selected = [x for x in selected if x != order_id]
    else:
        selected.append(order_id)
    await state.update_data(selected_order_ids=selected)
    stmt = (
        select(Order)
        .options(selectinload(Order.clinic))
        .where(
            Order.status == OrderStatus.READY_FOR_PICKUP,
            Order.delivery_type == DeliveryType.COURIER
        )
        .order_by(Order.is_urgent.desc(), Order.created_at.asc())
    )
    result = await session.execute(stmt)
    orders = result.scalars().all()
    text = (
        "📦 *Выберите заказы для доставки*\n\n"
        f"Выбрано: {len(selected)} зак." + (f" — #{', #'.join(map(str, sorted(selected)))}" if selected else "") + "\n\n"
        "Нажмите «Построить маршрут» и отправьте геолокацию."
    )
    await callback.message.edit_text(
        text,
        reply_markup=get_courier_select_orders_kb(orders, selected),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "courier:build_route", CourierState.selecting_orders)
async def courier_build_route(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    """Переход к запросу геолокации по выбранным заказам."""
    if not await is_courier(callback.from_user.id, session):
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    data = await state.get_data()
    selected = data.get("selected_order_ids") or []
    if not selected:
        await callback.answer("Сначала выберите хотя бы один заказ", show_alert=True)
        return
    await state.set_state(CourierState.waiting_location)
    await callback.message.edit_text(
        f"📍 Отправьте геолокацию для построения маршрута по {len(selected)} выбранным заказам."
    )
    await callback.message.answer("Нажмите кнопку для отправки геолокации:", reply_markup=get_courier_reply_kb())
    await callback.answer()


@router.callback_query(F.data == "courier:back")
async def courier_back(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    """Назад в главное меню курьера."""
    if not await is_courier(callback.from_user.id, session):
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    await state.clear()
    from keyboards.courier_kbs import get_courier_menu_kb
    await callback.message.edit_text("Панель курьера. Выберите действие:", reply_markup=get_courier_menu_kb())
    await callback.answer()


@router.message(Command("courier"))
async def cmd_courier(message: types.Message, session: AsyncSession):
    if not await is_courier(message.from_user.id, session):
        return
    from keyboards.courier_kbs import get_courier_menu_kb
    await message.answer("Панель курьера. Выберите заказы для доставки, затем отправьте геолокацию.", reply_markup=get_courier_menu_kb())

@router.message(F.location)
async def process_location_search(message: types.Message, state: FSMContext, session: AsyncSession):
    if not await is_courier(message.from_user.id, session):
        return

    lat = message.location.latitude
    lon = message.location.longitude
    data = await state.get_data()
    selected_ids = data.get("selected_order_ids") or []

    if selected_ids:
        # Курьер заранее выбрал заказы — строим маршрут только по ним
        stmt = (
            select(Order)
            .options(selectinload(Order.clinic))
            .where(
                Order.id.in_(selected_ids),
                Order.status == OrderStatus.READY_FOR_PICKUP,
                Order.delivery_type == DeliveryType.COURIER
            )
        )
        result = await session.execute(stmt)
        orders = result.scalars().all()
        await state.update_data(selected_order_ids=[])
    else:
        # Старое поведение: все заказы в радиусе
        stmt = (
            select(Order)
            .options(selectinload(Order.clinic))
            .where(
                Order.status == OrderStatus.READY_FOR_PICKUP,
                Order.delivery_type == DeliveryType.COURIER
            )
        )
        result = await session.execute(stmt)
        orders = result.scalars().all()

    if not orders:
        await message.answer("Нет заказов, готовых к выдаче (курьерская доставка).")
        return

    # Prepare data for routing; for pre-selected orders skip radius filter
    orders_map = []
    filtered_count = 0
    for o in orders:
        distance = haversine_distance(lat, lon, o.clinic.geo_lat, o.clinic.geo_lon)
        if selected_ids or distance <= MAX_RADIUS_KM:
            orders_map.append({
                'id': o.id,
                'lat': o.clinic.geo_lat,
                'lon': o.clinic.geo_lon,
                'clinic_name': o.clinic.name,
                'distance': distance,
                'obj': o
            })
        else:
            filtered_count += 1

    if not orders_map:
        if filtered_count > 0:
            await message.answer(
                f"❌ Нет заказов в радиусе {MAX_RADIUS_KM} км от вашего местоположения.\n"
                f"Найдено {filtered_count} заказов вне радиуса."
            )
        else:
            await message.answer("Нет заказов, готовых к выдаче (курьерская доставка).")
        return
    
    # Кластеризация: групповой маршрут (близкие точки) + отдельные (вдали 8+ км)
    grouped_route, distant_orders, total_grouped_dist = await optimize_route_with_clusters(
        (lat, lon), orders_map
    )

    grouped_ids = [item['id'] for item in grouped_route]
    distant_ids = [item['id'] for item in distant_orders]
    all_ids = grouped_ids + distant_ids

    map_url = generate_yandex_maps_url(grouped_route) if grouped_route else None

    text_parts = []
    if grouped_route:
        dist_str = f"{total_grouped_dist:.1f}"
        text_parts.append(
            f"📍 *Маршрут по близким точкам* ({len(grouped_route)} заказов, ~{dist_str} км)\n"
        )
        for idx, item in enumerate(grouped_route, 1):
            icon = "🔥" if item.get('obj') and item['obj'].is_urgent else "🟢"
            text_parts.append(f"{idx}. {icon} {item['clinic_name']} (#{item['id']})\n")

    if distant_orders:
        text_parts.append(f"\n📦 *Отдельные заказы (вдали 8+ км)*\n")
        for item in distant_orders:
            icon = "🔥" if item.get('obj') and item['obj'].is_urgent else "🟢"
            dist_to = haversine_distance(lat, lon, item['lat'], item['lon'])
            text_parts.append(f"• {icon} {item['clinic_name']} (#{item['id']}) — {dist_to:.1f} км\n")

    if filtered_count > 0:
        text_parts.append(f"\n⚠️ {filtered_count} заказов вне радиуса не включены.")

    text = "".join(text_parts)

    route_data = grouped_route + distant_orders
    await state.update_data(
        sorted_order_ids=all_ids,
        grouped_order_ids=grouped_ids,
        distant_order_ids=distant_ids,
        route_data=route_data,
    )

    await message.answer(text, reply_markup=get_route_action_kb(
        route_url=map_url,
        grouped_ids=grouped_ids,
        distant_ids=distant_ids,
    ), parse_mode="Markdown")
    await state.set_state(CourierState.viewing_route)

@router.callback_query(F.data == "take_route", CourierState.viewing_route)
async def take_route(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    ids = data.get('grouped_order_ids') or data.get('sorted_order_ids', [])
    
    if not ids:
        await callback.answer("Маршрут устарел.", show_alert=True)
        return
        
    # Update statuses to DELIVERING
    # Also assign courier_id? The model has courier_id.
    user_result = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
    courier_user = user_result.scalar_one()
    
    # Батчинг: обновляем все заказы, затем один commit
    for order_id in ids:
        stmt = select(Order).where(Order.id == order_id)
        res = await session.execute(stmt)
        order = res.scalar_one()
        
        # Ensure status is still correct
        if order.status == OrderStatus.READY_FOR_PICKUP:
            old_status = order.status
            order.status = OrderStatus.DELIVERING
            order.courier_id = courier_user.id
    
    await session.commit()
    
    # Уведомляем менеджеров о всех заказах (clinic и manager нужны для notify — без lazy load)
    from services.notifications import notify_manager_about_order_status
    for order_id in ids:
        stmt = select(Order).options(
            selectinload(Order.clinic), selectinload(Order.manager)
        ).where(Order.id == order_id)
        res = await session.execute(stmt)
        order = res.scalar_one_or_none()
        if order and order.status == OrderStatus.DELIVERING:
            await notify_manager_about_order_status(
                callback.bot, order, OrderStatus.READY_FOR_PICKUP, OrderStatus.DELIVERING, session
            )
    
    await callback.message.edit_text("✅ Вы взяли маршрут! Удачной дороги.")
    
    # Show list of active deliveries with "Delivered" buttons
    # We could send separate messages or a list. 
    # Let's send a message for each order to allow individual closing.
    await send_delivery_cards(callback.message, ids, session)
    await state.set_state(CourierState.delivering)

async def send_delivery_cards(message: types.Message, order_ids: list, session: AsyncSession):
    """Отправка карточек заказов с номерами в маршруте, навигатором и кнопкой завершения"""
    for idx, order_id in enumerate(order_ids, 1):
        stmt = select(Order).options(selectinload(Order.clinic)).where(Order.id == order_id)
        res = await session.execute(stmt)
        order = res.scalar_one_or_none()
        if order:
            # Генерируем ссылку на навигатор для этого заказа
            nav_url = order.clinic.navigator_link if order.clinic.navigator_link else (
                f"https://yandex.ru/maps/?pt={order.clinic.geo_lon},{order.clinic.geo_lat}&z=16"
            )
            
            info = (
                f"📦 *Заказ #{order.id}* (№{idx} в маршруте)\n\n"
                f"🏥 *Клиника:* {order.clinic.name}\n"
                f"📍 *Адрес:* {order.clinic.address}"
            )
            if order.is_urgent:
                info += "\n\n🔥 *СРОЧНЫЙ ЗАКАЗ*"
            
            await message.answer(
                info, 
                reply_markup=get_delivery_kb(order.id, nav_url, idx, len(order_ids)), 
                parse_mode="Markdown"
            )

@router.callback_query(F.data == "show_distant_orders")
async def show_distant_orders(callback: types.CallbackQuery, state: FSMContext):
    """Показать список отдельно доставляемых заказов (вдали 8+ км)"""
    data = await state.get_data()
    order_ids = data.get('distant_order_ids', [])
    route_data = data.get('route_data', [])
    order_id_to_urgent = {item['id']: getattr(item.get('obj'), 'is_urgent', False) for item in route_data if 'obj' in item}

    if not order_ids:
        await callback.answer("Нет отдельных заказов", show_alert=True)
        return

    await callback.message.edit_text(
        "📦 *Отдельные заказы (вдали 8+ км)*\n\nВыберите заказ для принятия:",
        parse_mode="Markdown",
        reply_markup=get_single_orders_kb(order_ids, order_id_to_urgent)
    )
    await callback.answer()


@router.callback_query(F.data == "show_single_orders")
async def show_single_orders(callback: types.CallbackQuery, state: FSMContext):
    """Показать список всех заказов по отдельности"""
    data = await state.get_data()
    order_ids = data.get('sorted_order_ids', [])
    route_data = data.get('route_data', [])
    order_id_to_urgent = {item['id']: getattr(item.get('obj'), 'is_urgent', False) for item in route_data if 'obj' in item}
    
    if not order_ids:
        await callback.answer("Заказы не найдены", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📦 *Отдельные заказы*\n\nВыберите заказ для принятия:",
        parse_mode="Markdown",
        reply_markup=get_single_orders_kb(order_ids, order_id_to_urgent)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("take_single_order:"))
async def take_single_order(callback: types.CallbackQuery, session: AsyncSession, state: FSMContext):
    """Принять отдельный заказ"""
    order_id = int(callback.data.split(":")[1])
    
    user_result = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
    courier_user = user_result.scalar_one_or_none()
    
    if not courier_user:
        await callback.answer("Ошибка: курьер не найден", show_alert=True)
        return
    
    stmt = select(Order).options(
        selectinload(Order.clinic), selectinload(Order.manager)
    ).where(Order.id == order_id)
    res = await session.execute(stmt)
    order = res.scalar_one_or_none()
    
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    
    if order.status != OrderStatus.READY_FOR_PICKUP:
        await callback.answer("Заказ уже взят или не готов к выдаче", show_alert=True)
        return
    
    old_status = order.status
    order.status = OrderStatus.DELIVERING
    order.courier_id = courier_user.id
    await session.commit()
    
    # Сначала показываем карточку доставки — чтобы курьер мог завершить заказ
    # Уведомление менеджера — после, чтобы ошибка notify не мешала
    nav_url = order.clinic.navigator_link if order.clinic.navigator_link else (
        f"https://yandex.ru/maps/?pt={order.clinic.geo_lon},{order.clinic.geo_lat}&z=16"
    )
    
    info = (
        f"✅ *Заказ #{order.id} взят в доставку*\n\n"
        f"🏥 *Клиника:* {order.clinic.name}\n"
        f"📍 *Адрес:* {order.clinic.address}"
    )
    if order.is_urgent:
        info += "\n\n🔥 *СРОЧНЫЙ ЗАКАЗ*"
    
    await callback.message.edit_text(
        info, 
        parse_mode="Markdown", 
        reply_markup=get_delivery_kb(order.id, nav_url)
    )
    await state.set_state(CourierState.delivering)
    await callback.answer()
    
    # Уведомляем менеджера (clinic и manager уже загружены — без lazy load)
    from services.notifications import notify_manager_about_order_status
    try:
        await notify_manager_about_order_status(
            callback.bot, order, old_status, OrderStatus.DELIVERING, session
        )
    except Exception:
        pass  # Не блокируем курьера при ошибке уведомления

@router.callback_query(F.data.startswith("take_combined_route:"))
async def take_combined_route(callback: types.CallbackQuery, session: AsyncSession, state: FSMContext):
    """Принять объединенный маршрут"""
    order_ids_str = callback.data.split(":")[1]
    order_ids = [int(id_str) for id_str in order_ids_str.split(",")]
    
    user_result = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
    courier_user = user_result.scalar_one_or_none()
    
    if not courier_user:
        await callback.answer("Ошибка: курьер не найден", show_alert=True)
        return
    
    # Обновляем статусы всех заказов
    orders_data = []
    for order_id in order_ids:
        stmt = select(Order).options(selectinload(Order.clinic)).where(Order.id == order_id)
        res = await session.execute(stmt)
        order = res.scalar_one_or_none()
        
        if order and order.status == OrderStatus.READY_FOR_PICKUP:
            old_status = order.status
            order.status = OrderStatus.DELIVERING
            order.courier_id = courier_user.id
            orders_data.append({
                'order_id': order.id,
                'name': order.clinic.name,
                'address': order.clinic.address
            })
    
    await session.commit()
    
    # Уведомляем менеджеров о всех заказах (clinic и manager — без lazy load)
    from services.notifications import notify_manager_about_order_status
    for order_id in order_ids:
        stmt = select(Order).options(
            selectinload(Order.clinic), selectinload(Order.manager)
        ).where(Order.id == order_id)
        res = await session.execute(stmt)
        order = res.scalar_one_or_none()
        if order and order.status == OrderStatus.DELIVERING:
            await notify_manager_about_order_status(
                callback.bot, order, OrderStatus.READY_FOR_PICKUP, OrderStatus.DELIVERING, session
            )
    
    # Сохраняем информацию о объединенном маршруте в state
    await state.update_data(
        combined_route_ids=order_ids,
        delivered_order_ids=[],
        is_combined_route=True
    )
    
    # Отправляем карточки для каждого заказа с навигатором и номерами
    for idx, order_id in enumerate(order_ids, 1):
        stmt = select(Order).options(selectinload(Order.clinic)).where(Order.id == order_id)
        res = await session.execute(stmt)
        order = res.scalar_one_or_none()
        if order:
            # Генерируем ссылку на навигатор
            nav_url = order.clinic.navigator_link if order.clinic.navigator_link else (
                f"https://yandex.ru/maps/?pt={order.clinic.geo_lon},{order.clinic.geo_lat}&z=16"
            )
            
            info = (
                f"📦 *Заказ #{order.id}* (№{idx} в маршруте)\n\n"
                f"🏥 *Клиника:* {order.clinic.name}\n"
                f"📍 *Адрес:* {order.clinic.address}"
            )
            if order.is_urgent:
                info += "\n\n🔥 *СРОЧНЫЙ ЗАКАЗ*"
            
            await callback.message.answer(
                info,
                reply_markup=get_delivery_kb(order.id, nav_url, idx, len(order_ids)),
                parse_mode="Markdown"
            )
    
    text = (
        f"✅ *Объединенный маршрут взят в доставку*\n\n"
        f"Заказов в маршруте: {len(orders_data)}\n\n"
        f"Используйте кнопки навигатора и завершения для каждого заказа."
    )
    
    await callback.message.edit_text(text, parse_mode="Markdown")
    await state.set_state(CourierState.delivering_combined)
    await callback.answer()

@router.callback_query(F.data.startswith("combined_delivered:"))
async def mark_combined_delivered(callback: types.CallbackQuery, session: AsyncSession, state: FSMContext):
    """Отметить доставку заказа из объединенного маршрута"""
    order_id = int(callback.data.split(":")[1])
    
    data = await state.get_data()
    combined_ids = data.get('combined_route_ids', [])
    delivered_ids = data.get('delivered_order_ids', [])
    
    if order_id not in combined_ids:
        await callback.answer("Этот заказ не в текущем маршруте", show_alert=True)
        return
    
    if order_id in delivered_ids:
        await callback.answer("Этот заказ уже отмечен как доставленный", show_alert=True)
        return
    
    # Отмечаем заказ как доставленный
    stmt = select(Order).options(
        selectinload(Order.clinic),
        selectinload(Order.manager),
    ).where(Order.id == order_id)
    res = await session.execute(stmt)
    order = res.scalar_one_or_none()
    
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    
    if order.status != OrderStatus.DELIVERING:
        await callback.answer("Заказ не в статусе доставки", show_alert=True)
        return
    
    old_status = order.status
    order.status = OrderStatus.DELIVERED
    order.delivered_at = datetime.now(timezone.utc)
    await session.commit()
    from services.notifications import notify_manager_about_order_status
    await notify_manager_about_order_status(
        callback.bot, order, old_status, OrderStatus.DELIVERED, session
    )
    
    # Добавляем в список доставленных
    delivered_ids.append(order_id)
    await state.update_data(delivered_order_ids=delivered_ids)
    
    # Проверяем, все ли заказы доставлены
    if len(delivered_ids) == len(combined_ids):
        # Все заказы доставлены - закрываем маршрут
        await callback.message.edit_text(
            f"✅ *Все заказы из объединенного маршрута доставлены!*\n\n"
            f"Доставлено заказов: {len(delivered_ids)}",
            parse_mode="Markdown"
        )
        await state.clear()
    else:
        # Обновляем клавиатуру - убираем доставленный заказ
        remaining_orders = [oid for oid in combined_ids if oid not in delivered_ids]
        
        clinics = []
        for oid in remaining_orders:
            stmt = select(Order).options(selectinload(Order.clinic)).where(Order.id == oid)
            res = await session.execute(stmt)
            order = res.scalar_one_or_none()
            if order:
                clinics.append({'order_id': order.id, 'name': order.clinic.name, 'is_urgent': order.is_urgent})
        
        kb = get_combined_delivery_kb(remaining_orders, clinics)
        
        await callback.message.edit_text(
            f"✅ *Заказ #{order_id} доставлен в {order.clinic.name}*\n\n"
            f"Осталось доставить: {len(remaining_orders)} заказов",
            parse_mode="Markdown",
            reply_markup=kb
        )
    
    await callback.answer()

@router.callback_query(F.data.startswith("courier_delivered:"))
async def mark_delivered(callback: types.CallbackQuery, session: AsyncSession):
    order_id = int(callback.data.split(":")[1])
    
    stmt = select(Order).options(
        selectinload(Order.manager),
        selectinload(Order.clinic),
    ).where(Order.id == order_id)
    res = await session.execute(stmt)
    order = res.scalar_one_or_none()
    
    if order:
        # Check if order is assigned to this courier or is free
        user_result = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
        courier_user = user_result.scalar_one_or_none()
        
        if not courier_user:
            await callback.answer("Ошибка: курьер не найден", show_alert=True)
            return
        
        # Check if order is assigned to this courier or is free (no courier assigned)
        if order.courier_id is not None and order.courier_id != courier_user.id:
            await callback.answer("❌ Этот заказ назначен другому курьеру", show_alert=True)
            return
        
        if order.status != OrderStatus.DELIVERING:
            await callback.answer("❌ Заказ не в статусе 'В доставке'", show_alert=True)
            return
        
        old_status = order.status
        order.status = OrderStatus.DELIVERED
        order.delivered_at = datetime.now(timezone.utc)
        # Ensure courier_id is set
        if order.courier_id is None:
            order.courier_id = courier_user.id
        await session.commit()
        from services.notifications import notify_manager_about_order_status
        await notify_manager_about_order_status(
            callback.bot, order, old_status, OrderStatus.DELIVERED, session
        )
        await callback.message.edit_text(f"✅ Заказ #{order_id} доставлен.")
    else:
        await callback.answer("Ошибка обновления.", show_alert=True)
