from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_courier_menu_kb() -> InlineKeyboardMarkup:
    # Request location button
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Найти маршрут", request_location=True)] # Wait, request_location is for ReplyKeyboard!
        # Inline buttons CANNOT request location directly. We need a Reply Keyboard or ask user to attach.
        # "Кнопка [🚀 Найти маршрут]. Запрашивает геопозицию." is usually implemented as a Reply Button.
        # OR text message "Send geo".
    ])
    
def get_courier_reply_kb():
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🚀 Найти маршрут", request_location=True)]],
        resize_keyboard=True
    )

def get_route_action_kb(
    route_url: str = None,
    grouped_ids: list = None,
    distant_ids: list = None,
) -> InlineKeyboardMarkup:
    """
    Клавиатура для действий с маршрутом.
    grouped_ids — заказы в групповом маршруте (близкие точки).
    distant_ids — отдельные заказы вдали (8+ км).
    """
    rows = []
    grouped_ids = grouped_ids or []
    distant_ids = distant_ids or []

    # Маршрут по групповым точкам
    if grouped_ids:
        if route_url:
            rows.append([
                InlineKeyboardButton(text="🗺 Открыть групповой маршрут", url=route_url)
            ])
        if len(grouped_ids) >= 2:
            order_ids_str = ",".join(map(str, grouped_ids))
            rows.append([
                InlineKeyboardButton(
                    text=f"✅ Взять групповой маршрут ({len(grouped_ids)} заказов)",
                    callback_data=f"take_combined_route:{order_ids_str}"
                )
            ])
        else:
            rows.append([
                InlineKeyboardButton(text="✅ Взять маршрут", callback_data="take_route")
            ])

    # Отдельные заказы (вдали)
    if distant_ids:
        rows.append([
            InlineKeyboardButton(text="📦 Отдельные заказы (вдали)", callback_data="show_distant_orders")
        ])

    # Показать все по отдельности (если есть и групповые, и отдельные)
    if grouped_ids or distant_ids:
        rows.append([
            InlineKeyboardButton(text="📦 Все заказы по отдельности", callback_data="show_single_orders")
        ])

    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_single_orders_kb(order_ids: list, order_id_to_urgent: dict = None) -> InlineKeyboardMarkup:
    """Клавиатура со списком отдельных заказов. order_id_to_urgent: {order_id: is_urgent} для иконок."""
    rows = []
    order_id_to_urgent = order_id_to_urgent or {}
    for order_id in order_ids:
        icon = "🔥" if order_id_to_urgent.get(order_id) else "🟢"
        rows.append([
            InlineKeyboardButton(
                text=f"{icon} Заказ #{order_id}", 
                callback_data=f"take_single_order:{order_id}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_delivery_kb(order_id: int, nav_url: str = None, route_number: int = None, total_orders: int = None) -> InlineKeyboardMarkup:
    """
    Клавиатура для заказа в доставке.
    
    Args:
        order_id: ID заказа
        nav_url: URL навигатора для клиники
        route_number: Номер заказа в маршруте (1, 2, 3...)
        total_orders: Общее количество заказов в маршруте
    """
    rows = []
    
    # Кнопка навигатора
    if nav_url:
        rows.append([
            InlineKeyboardButton(text="🗺 Открыть в навигаторе", url=nav_url)
        ])
    
    # Кнопка завершения заказа
    button_text = "✅ Завершить доставку"
    if route_number and total_orders:
        button_text = f"✅ Завершить ({route_number}/{total_orders})"
    
    rows.append([
        InlineKeyboardButton(text=button_text, callback_data=f"courier_delivered:{order_id}")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_combined_delivery_kb(order_ids: list, clinics: list) -> InlineKeyboardMarkup:
    """Клавиатура для выбора клиники при доставке объединенного заказа. clinics: [{'order_id', 'name', 'is_urgent'?}]"""
    rows = []
    for clinic in clinics:
        icon = "🔥" if clinic.get('is_urgent') else "🟢"
        rows.append([
            InlineKeyboardButton(
                text=f"{icon} Доставлено в {clinic['name']} (Заказ #{clinic['order_id']})",
                callback_data=f"combined_delivered:{clinic['order_id']}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_courier_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню курьера"""
    rows = [
        [InlineKeyboardButton(text="🚀 Найти маршрут", callback_data="courier:find_route")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)