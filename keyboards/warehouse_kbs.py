from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.models import Order, OrderStatus

def get_warehouse_orders_list_kb(orders: list) -> InlineKeyboardMarkup:
    """Список активных заказов в виде кнопок. При нажатии — детали заказа."""
    rows = []
    # По 2 кнопки в строке
    for i in range(0, len(orders), 2):
        row = []
        for j in range(2):
            if i + j < len(orders):
                o = orders[i + j]
                icon = "🔥" if o.is_urgent else "🟢"
                row.append(InlineKeyboardButton(
                    text=f"{icon} #{o.id}",
                    callback_data=f"warehouse:order:{o.id}"
                ))
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_warehouse_order_detail_kb(order_id: int, status: str) -> InlineKeyboardMarkup:
    """
    Кнопки для детального просмотра заказа.
    NEW -> "Взять в работу"
    ASSEMBLY -> "Собрано"
    """
    rows = []
    if status == "new":
        rows.append([InlineKeyboardButton(text="🛠 Взять в работу", callback_data=f"wh_take:{order_id}")])
    elif status == "assembly":
        rows.append([InlineKeyboardButton(text="📦 Собрано", callback_data=f"wh_ready:{order_id}")])
    rows.append([InlineKeyboardButton(text="⬅ К списку заказов", callback_data="warehouse:orders")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_warehouse_order_kb(order_id: int, status: str) -> InlineKeyboardMarkup:
    """Алиас для совместимости. Использует get_warehouse_order_detail_kb."""
    return get_warehouse_order_detail_kb(order_id, status)

def get_warehouse_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню склада"""
    rows = [
        [InlineKeyboardButton(text="📦 Активные заказы", callback_data="warehouse:orders")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)