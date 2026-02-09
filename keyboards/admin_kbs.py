from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData
from database.models import UserRole

class RoleCallbackFactory(CallbackData, prefix="role"):
    user_id: int
    role: str
    action: str # 'approve', 'reject'

class ClinicCallbackFactory(CallbackData, prefix="clinic"):
    clinic_id: int
    action: str  # 'edit', 'cancel', 'select_field'
    field: str = ""  # 'name', 'doctor_name', 'phone', 'address', 'location', 'chat_id'; '' для edit/cancel

class UserManageCallbackFactory(CallbackData, prefix="usr"):
    user_id: int
    action: str  # set_role | toggle_active | delete | delete_confirm | cancel
    role: str | None = None

def get_role_assignment_kb(user_id: int) -> InlineKeyboardMarkup:
    builder = []
    
    # Rows for roles
    roles = [
        ("Менеджер", UserRole.MANAGER),
        ("Склад", UserRole.WAREHOUSE),
        ("Курьер", UserRole.COURIER)
    ]
    
    kb_rows = []
    for label, role_enum in roles:
        kb_rows.append([
            InlineKeyboardButton(
                text=label, 
                callback_data=RoleCallbackFactory(user_id=user_id, role=role_enum.value, action="approve").pack()
            )
        ])
    
    # Reject button
    kb_rows.append([
        InlineKeyboardButton(
            text="Отклонить", 
            callback_data=RoleCallbackFactory(user_id=user_id, role="none", action="reject").pack()
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=kb_rows)

def get_user_manage_kb(user_id: int, *, is_protected: bool = False, is_active: bool | None = None) -> InlineKeyboardMarkup:
    """
    Клавиатура управления пользователем: данные и роль, смена роли, исключение, удаление.
    is_protected=True — только просмотр (врач клиники). is_active — для кнопки «Исключить»/«Вернуть».
    """
    if is_protected:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔒 Изменения запрещены (врач клиники)", callback_data="noop")]
            ]
        )

    toggle_text = "↩ Вернуть в доступ" if is_active is False else "🚫 Исключить из доступа"
    rows = [
        [
            InlineKeyboardButton(
                text="Менеджер",
                callback_data=UserManageCallbackFactory(user_id=user_id, action="set_role", role=UserRole.MANAGER.value).pack(),
            ),
            InlineKeyboardButton(
                text="Склад",
                callback_data=UserManageCallbackFactory(user_id=user_id, action="set_role", role=UserRole.WAREHOUSE.value).pack(),
            ),
            InlineKeyboardButton(
                text="Курьер",
                callback_data=UserManageCallbackFactory(user_id=user_id, action="set_role", role=UserRole.COURIER.value).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text=toggle_text,
                callback_data=UserManageCallbackFactory(user_id=user_id, action="toggle_active").pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="🗑 Удалить",
                callback_data=UserManageCallbackFactory(user_id=user_id, action="delete").pack(),
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_user_delete_confirm_kb(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да, удалить",
                    callback_data=UserManageCallbackFactory(user_id=user_id, action="delete_confirm").pack(),
                ),
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=UserManageCallbackFactory(user_id=user_id, action="cancel").pack(),
                ),
            ]
        ]
    )

def get_clinics_list_kb(clinics) -> InlineKeyboardMarkup:
    """Клавиатура: список клиник для редактирования + кнопка добавления новой"""
    rows = []
    for clinic in clinics:
        rows.append([
            InlineKeyboardButton(
                text=f"{clinic.name} ({clinic.doctor_name})",
                callback_data=ClinicCallbackFactory(clinic_id=clinic.id, action="edit", field="").pack()
            )
        ])
    rows.append([InlineKeyboardButton(text="➕ Добавить клинику", callback_data="admin:add_clinic")])
    rows.append([InlineKeyboardButton(text="⬅ В меню", callback_data="admin:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_clinic_edit_kb(clinic_id: int) -> InlineKeyboardMarkup:
    """Generate keyboard for selecting field to edit"""
    rows = [
        [InlineKeyboardButton(text="Название", callback_data=ClinicCallbackFactory(clinic_id=clinic_id, action="select_field", field="name").pack())],
        [InlineKeyboardButton(text="ФИО врача", callback_data=ClinicCallbackFactory(clinic_id=clinic_id, action="select_field", field="doctor_name").pack())],
        [InlineKeyboardButton(text="Телефон", callback_data=ClinicCallbackFactory(clinic_id=clinic_id, action="select_field", field="phone").pack())],
        [InlineKeyboardButton(text="Адрес", callback_data=ClinicCallbackFactory(clinic_id=clinic_id, action="select_field", field="address").pack())],
        [InlineKeyboardButton(text="Геолокация", callback_data=ClinicCallbackFactory(clinic_id=clinic_id, action="select_field", field="location").pack())],
        [InlineKeyboardButton(text="Chat ID врача", callback_data=ClinicCallbackFactory(clinic_id=clinic_id, action="select_field", field="chat_id").pack())],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=ClinicCallbackFactory(clinic_id=clinic_id, action="cancel", field="").pack())]
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_admin_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню администратора"""
    rows = [
        [InlineKeyboardButton(text="👥 Управление пользователями", callback_data="admin:users")],
        [InlineKeyboardButton(text="🏥 Клиники", callback_data="admin:clinics")],
        [InlineKeyboardButton(text="📊 Отчеты", callback_data="admin:reports")],
        [InlineKeyboardButton(text="📈 Статистика продукции", callback_data="admin:product_stats")],
        [InlineKeyboardButton(text="— Тест панелей ролей —", callback_data="noop")],
        [InlineKeyboardButton(text="🛍 Панель менеджера", callback_data="admin:panel_manager")],
        [InlineKeyboardButton(text="📦 Панель склада", callback_data="admin:panel_warehouse")],
        [InlineKeyboardButton(text="🚚 Панель курьера", callback_data="admin:panel_courier")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)