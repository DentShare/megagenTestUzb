import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import UserRole, Clinic
from services.db_ops import approve_user_role, create_clinic, get_all_clinics, get_clinic_by_id, update_clinic_field
from services.reports import generate_report_data, export_to_sheets, generate_product_statistics, format_product_statistics
from keyboards.admin_kbs import (
    RoleCallbackFactory,
    ClinicCallbackFactory,
    UserManageCallbackFactory,
    get_clinics_list_kb,
    get_clinic_edit_kb,
    get_admin_menu_kb,
    get_user_manage_kb,
    get_user_delete_confirm_kb,
)
from keyboards.manager_kbs import get_manager_menu_kb
from keyboards.warehouse_kbs import get_warehouse_menu_kb
from keyboards.courier_kbs import get_courier_menu_kb
from states.admin_states import AddClinicState, EditClinicState, ProductStatsState
from config import config
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from database.models import Order
from database.models import User
from keyboards.admin_kbs import get_role_assignment_kb
from services.cache import user_cache

logger = logging.getLogger(__name__)
router = Router()

def is_admin(telegram_id: int) -> bool:
    return telegram_id in config.ADMIN_IDS_LIST


def _format_user_card(user, clinic_name: str | None = None) -> str:
    """Текст карточки сотрудника: данные, роль, активность. Без Markdown."""
    active = "да" if user.is_active else "нет"
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    lines = [
        f"👤 {user.full_name}",
        f"ID: {user.telegram_id}",
        f"Роль: {role}",
        f"Активен: {active}",
    ]
    if clinic_name:
        lines.append(f"🔒 Врач клиники: {clinic_name}")
    return "\n".join(lines)


# --- Role Assignment ---
@router.callback_query(RoleCallbackFactory.filter())
async def process_role_callback(callback: types.CallbackQuery, callback_data: RoleCallbackFactory, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("Вы не администратор.", show_alert=True)
        return

    user_telegram_id = callback_data.user_id
    action = callback_data.action
    
    if action == "reject":
        await callback.message.edit_text(f"Пользователь {user_telegram_id} отклонен.")
        try:
            await callback.bot.send_message(user_telegram_id, "Ваша регистрация отклонена.")
        except Exception as e:
            logger.error(f"Failed to notify user {user_telegram_id} about rejection: {e}", exc_info=True)
        return

    role_enum = UserRole(callback_data.role)
    user = await approve_user_role(session, user_telegram_id, role_enum)
    
    if user:
        await callback.message.edit_text(
            f"Пользователь {user.full_name} активирован с ролью {role_enum.value}."
        )
        try:
            await callback.bot.send_message(
                user_telegram_id, 
                f"Вам выдан доступ. Ваша роль: {role_enum.value}"
            )
        except (TelegramBadRequest, Exception) as e:
            logger.warning(
                f"Failed to notify user {user_telegram_id} about approval: {e}",
                exc_info=True,
                extra={"user_id": user_telegram_id, "role": role_enum.value}
            )
            await callback.message.answer(f"⚠️ Не удалось уведомить пользователя: {e}")
    else:
        await callback.message.answer("Пользователь не найден в БД.")
    await callback.answer()

# --- Add Clinic FSM ---
@router.message(Command("add_clinic"))
async def start_add_clinic(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    await message.answer("Введите название клиники:")
    await state.set_state(AddClinicState.waiting_for_name)

@router.message(AddClinicState.waiting_for_name)
async def process_clinic_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите ФИО врача:")
    await state.set_state(AddClinicState.waiting_for_doctor_name)

@router.message(AddClinicState.waiting_for_doctor_name)
async def process_doctor_name(message: types.Message, state: FSMContext):
    await state.update_data(doctor_name=message.text)
    await message.answer("Введите номер телефона врача/клиники:")
    await state.set_state(AddClinicState.waiting_for_phone)

@router.message(AddClinicState.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone_number=message.text)
    await message.answer("Введите адрес клиники:")
    await state.set_state(AddClinicState.waiting_for_address)

@router.message(AddClinicState.waiting_for_address)
async def process_address(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text)
    await message.answer("Отправьте геолокацию клиники (скрепка -> Геопозиция):")
    await state.set_state(AddClinicState.waiting_for_location)

@router.message(AddClinicState.waiting_for_location, F.location)
async def process_location(message: types.Message, state: FSMContext):
    lat = message.location.latitude
    lon = message.location.longitude
    await state.update_data(geo_lat=lat, geo_lon=lon)
    await message.answer(
        "Введите Telegram Chat ID врача (число) или «пропустить», чтобы добавить позже при редактировании:"
    )
    await state.set_state(AddClinicState.waiting_for_chat_id)

# Варианты ввода для пропуска Chat ID
_SKIP_CHAT_ID = frozenset({"пропустить", "skip", "0", "-", "нет", "no", "позже", "later"})

@router.message(AddClinicState.waiting_for_chat_id)
async def process_chat_id(message: types.Message, state: FSMContext, session: AsyncSession):
    """Обработка Chat ID: число или пропуск."""
    text = (message.text or "").strip().lower()
    chat_id = None
    if text not in _SKIP_CHAT_ID:
        try:
            from services.validation import ChatIDInput
            chat_input = ChatIDInput.from_string(message.text)
            chat_id = chat_input.chat_id
        except ValueError as e:
            await message.answer(f"❌ {str(e)}\nИли введите «пропустить», чтобы не указывать Chat ID.")
            return

    data = await state.get_data()
    
    await create_clinic(
        session=session,
        name=data['name'],
        doctor_name=data['doctor_name'],
        address=data['address'],
        geo_lat=data['geo_lat'],
        geo_lon=data['geo_lon'],
        chat_id=chat_id,
        phone_number=data.get('phone_number')
    )
    
    if chat_id is None:
        await message.answer(f"Клиника «{data['name']}» добавлена. Chat ID можно указать позже в разделе «Клиники» → редактирование.")
    else:
        await message.answer(f"Клиника «{data['name']}» успешно добавлена!")
    await state.clear()

# --- Edit Clinic ---
@router.message(Command("clinics"))
async def cmd_clinics(message: types.Message, session: AsyncSession):
    if not is_admin(message.from_user.id):
        return
    
    clinics = await get_all_clinics(session)
    
    if not clinics:
        await message.answer("Нет зарегистрированных клиник.")
        return
    
    await message.answer("Выберите клинику для редактирования:", reply_markup=get_clinics_list_kb(clinics))

@router.callback_query(ClinicCallbackFactory.filter(F.action == "edit"))
async def start_edit_clinic(callback: types.CallbackQuery, callback_data: ClinicCallbackFactory, state: FSMContext, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("Вы не администратор.", show_alert=True)
        return
    
    clinic_id = callback_data.clinic_id
    clinic = await get_clinic_by_id(session, clinic_id)
    if not clinic:
        await callback.answer("Клиника не найдена.", show_alert=True)
        return
    
    await state.update_data(clinic_id=clinic_id)
    
    text = (
        "Редактирование клиники\n\n"
        f"Название: {clinic.name}\n"
        f"Врач: {clinic.doctor_name}\n"
        f"Телефон: {clinic.phone_number or 'не указан'}\n"
        f"Адрес: {clinic.address}\n"
        f"Chat ID: {clinic.telegram_chat_id or 'не указан'}\n\n"
        "Выберите поле для редактирования:"
    )
    try:
        await callback.message.edit_text(text, reply_markup=get_clinic_edit_kb(clinic_id))
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            raise
    await state.set_state(EditClinicState.selecting_field)
    await callback.answer()

@router.callback_query(ClinicCallbackFactory.filter(F.action == "select_field"))
async def select_field_to_edit(callback: types.CallbackQuery, callback_data: ClinicCallbackFactory, state: FSMContext):
    field = (callback_data.field or "").strip()
    clinic_id = callback_data.clinic_id
    field_prompts = {
        "name": "Введите новое название клиники:",
        "doctor_name": "Введите новое ФИО врача:",
        "phone": "Введите новый номер телефона:",
        "address": "Введите новый адрес:",
        "location": "Отправьте новую геолокацию клиники (скрепка -> Геопозиция):",
        "chat_id": "Введите новый Telegram Chat ID врача (число):"
    }
    if field not in field_prompts:
        await callback.answer("Неизвестное поле.", show_alert=True)
        return
    if field == "location":
        await state.set_state(EditClinicState.waiting_for_location)
    elif field == "chat_id":
        await state.set_state(EditClinicState.waiting_for_chat_id)
    elif field == "name":
        await state.set_state(EditClinicState.waiting_for_name)
    elif field == "doctor_name":
        await state.set_state(EditClinicState.waiting_for_doctor_name)
    elif field == "phone":
        await state.set_state(EditClinicState.waiting_for_phone)
    elif field == "address":
        await state.set_state(EditClinicState.waiting_for_address)
    
    await state.update_data(editing_field=field, clinic_id=clinic_id)
    await callback.message.edit_text(field_prompts.get(field, "Введите новое значение:"))
    await callback.answer()

@router.callback_query(ClinicCallbackFactory.filter(F.action == "cancel"))
async def cancel_edit_clinic(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Редактирование отменено.")
    await state.clear()
    await callback.answer()

@router.message(EditClinicState.waiting_for_name)
async def process_edit_name(message: types.Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    clinic_id = data.get('clinic_id')
    
    clinic = await update_clinic_field(session, clinic_id, "name", message.text)
    if clinic:
        await message.answer(f"✅ Название клиники обновлено: {clinic.name}")
    else:
        await message.answer("❌ Ошибка обновления.")
    await state.clear()

@router.message(EditClinicState.waiting_for_doctor_name)
async def process_edit_doctor_name(message: types.Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    clinic_id = data.get('clinic_id')
    
    clinic = await update_clinic_field(session, clinic_id, "doctor_name", message.text)
    if clinic:
        await message.answer(f"✅ ФИО врача обновлено: {clinic.doctor_name}")
    else:
        await message.answer("❌ Ошибка обновления.")
    await state.clear()

@router.message(EditClinicState.waiting_for_phone)
async def process_edit_phone(message: types.Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    clinic_id = data.get('clinic_id')
    
    clinic = await update_clinic_field(session, clinic_id, "phone_number", message.text)
    if clinic:
        await message.answer(f"✅ Телефон обновлен: {clinic.phone_number}")
    else:
        await message.answer("❌ Ошибка обновления.")
    await state.clear()

@router.message(EditClinicState.waiting_for_address)
async def process_edit_address(message: types.Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    clinic_id = data.get('clinic_id')
    
    clinic = await update_clinic_field(session, clinic_id, "address", message.text)
    if clinic:
        await message.answer(f"✅ Адрес обновлен: {clinic.address}")
    else:
        await message.answer("❌ Ошибка обновления.")
    await state.clear()

@router.message(EditClinicState.waiting_for_location, F.location)
async def process_edit_location(message: types.Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    clinic_id = data.get('clinic_id')
    lat = message.location.latitude
    lon = message.location.longitude
    
    clinic = await update_clinic_field(session, clinic_id, "geo_lat", lat)
    if clinic:
        clinic = await update_clinic_field(session, clinic_id, "geo_lon", lon)
        if clinic:
            await message.answer(f"✅ Геолокация обновлена: {lat}, {lon}")
        else:
            await message.answer("❌ Ошибка обновления долготы.")
    else:
        await message.answer("❌ Ошибка обновления широты.")
    await state.clear()

@router.message(EditClinicState.waiting_for_chat_id)
async def process_edit_chat_id(message: types.Message, state: FSMContext, session: AsyncSession):
    """Обработка Chat ID с валидацией."""
    try:
        from services.validation import ChatIDInput
        chat_input = ChatIDInput.from_string(message.text)
        chat_id = chat_input.chat_id
    except ValueError as e:
        await message.answer(f"❌ {str(e)}")
        return
    
    data = await state.get_data()
    clinic_id = data.get('clinic_id')
    
    clinic = await update_clinic_field(session, clinic_id, "telegram_chat_id", chat_id)
    if clinic:
        await message.answer(f"✅ Chat ID обновлен: {clinic.telegram_chat_id}")
    else:
        await message.answer("❌ Ошибка обновления.")
    await state.clear()

# --- Main Menu Handlers ---
@router.callback_query(F.data == "admin:users")
async def admin_menu_users(callback: types.CallbackQuery, session: AsyncSession):
    """Показать список пользователей с пагинацией."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Вы не администратор.", show_alert=True)
        return

    # Защита: нельзя менять/удалять пользователей, которые используются как Chat ID врача клиники
    protected_result = await session.execute(
        select(Clinic.telegram_chat_id, Clinic.name).where(Clinic.telegram_chat_id.is_not(None))
    )
    protected_map = {int(chat_id): clinic_name for chat_id, clinic_name in protected_result.all() if chat_id is not None}

    # Пагинация
    from config import config
    from sqlalchemy import func
    page_size = config.USERS_PER_PAGE
    
    # Подсчет общего количества
    total_count = await session.scalar(select(func.count(User.id)))
    
    # Загружаем только первую страницу
    stmt = select(User).order_by(User.id.desc()).limit(page_size)
    result = await session.execute(stmt)
    users = list(result.scalars().all())

    if not users:
        try:
            await callback.message.edit_text(
                "✅ Пользователей в базе нет.",
                reply_markup=get_admin_menu_kb(),
            )
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise
        await callback.answer()
        return

    pending_count = sum(1 for u in users if not u.is_active)
    protected_count = sum(1 for u in users if u.telegram_id in protected_map)

    header = (
        "👥 Управление пользователями\n\n"
        f"Всего: {total_count}\n"
        f"Показано: {len(users)}\n"
        f"Ожидают активации: {pending_count}\n"
        f"Защищены (врач клиники): {protected_count}\n\n"
        "Карточки ниже: данные, роль. Можно менять роль, исключать или удалять."
    )
    try:
        await callback.message.edit_text(header, reply_markup=get_admin_menu_kb())
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise

    for u in users:
        is_protected = u.telegram_id in protected_map
        clinic_name = protected_map.get(u.telegram_id) if is_protected else None
        text = _format_user_card(u, clinic_name=clinic_name)
        kb = get_user_manage_kb(u.telegram_id, is_protected=is_protected, is_active=u.is_active)
        await callback.message.answer(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(UserManageCallbackFactory.filter())
async def manage_user_callback(callback: types.CallbackQuery, callback_data: UserManageCallbackFactory, session: AsyncSession):
    """Смена роли/активация/удаление пользователя (с защитой врачей клиники)."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Вы не администратор.", show_alert=True)
        return

    user_telegram_id = callback_data.user_id

    # Защита врачей: если этот ID используется как Chat ID в клинике — запрещаем
    clinic_res = await session.execute(
        select(Clinic).where(Clinic.telegram_chat_id == user_telegram_id)
    )
    clinic = clinic_res.scalar_one_or_none()
    if clinic:
        await callback.answer("🔒 Этот пользователь указан как Chat ID врача в клинике. Изменения запрещены.", show_alert=True)
        return

    # Защита админов из ENV: чтобы случайно не сломать доступ
    if user_telegram_id in config.ADMIN_IDS_LIST and callback_data.action in ("delete", "delete_confirm", "set_role", "toggle_active"):
        await callback.answer("🔒 Это ADMIN_IDS. Изменения через панель запрещены.", show_alert=True)
        return

    res = await session.execute(select(User).where(User.telegram_id == user_telegram_id))
    user = res.scalar_one_or_none()
    if not user:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return

    action = callback_data.action

    if action == "set_role":
        if not callback_data.role:
            await callback.answer("Не указана роль.", show_alert=True)
            return
        role_enum = UserRole(callback_data.role)
        user.role = role_enum
        user.is_active = True  # при смене роли автоматически активируем
        await session.commit()
        await session.refresh(user)
        if user_cache is not None:
            try:
                await user_cache.invalidate(user_telegram_id)
            except Exception:
                pass
        try:
            await callback.message.edit_text(
                _format_user_card(user),
                reply_markup=get_user_manage_kb(user_telegram_id, is_protected=False, is_active=user.is_active),
            )
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e).lower():
                raise
        await callback.answer(f"Роль: {role_enum.value}")
        return

    if action == "toggle_active":
        user.is_active = not bool(user.is_active)
        await session.commit()
        await session.refresh(user)
        if user_cache is not None:
            try:
                await user_cache.invalidate(user_telegram_id)
            except Exception:
                pass
        try:
            await callback.message.edit_text(
                _format_user_card(user),
                reply_markup=get_user_manage_kb(user_telegram_id, is_protected=False, is_active=user.is_active),
            )
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e).lower():
                raise
        status = "в доступе" if user.is_active else "исключён"
        await callback.answer(f"Статус: {status}")
        return

    if action == "delete":
        try:
            await callback.message.edit_reply_markup(reply_markup=get_user_delete_confirm_kb(user_telegram_id))
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e).lower():
                raise
        await callback.answer("Подтвердите удаление", show_alert=True)
        return

    if action == "cancel":
        try:
            await callback.message.edit_text(
                _format_user_card(user),
                reply_markup=get_user_manage_kb(user_telegram_id, is_protected=False, is_active=user.is_active),
            )
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e).lower():
                raise
        await callback.answer("Отменено")
        return

    if action == "delete_confirm":
        orders_cnt = await session.scalar(
            select(func.count(Order.id)).where(
                (Order.manager_id == user.id) | (Order.courier_id == user.id)
            )
        )
        if orders_cnt and orders_cnt > 0:
            user.is_active = False
            await session.commit()
            await session.refresh(user)
            if user_cache is not None:
                try:
                    await user_cache.invalidate(user_telegram_id)
                except Exception:
                    pass
            try:
                await callback.message.edit_text(
                    _format_user_card(user),
                    reply_markup=get_user_manage_kb(user_telegram_id, is_protected=False, is_active=user.is_active),
                )
            except TelegramBadRequest as e:
                if "message is not modified" not in str(e).lower():
                    raise
            await callback.answer("Есть заказы. Пользователь исключён (деактивирован).", show_alert=True)
            return

        await session.delete(user)
        await session.commit()
        if user_cache is not None:
            try:
                await user_cache.invalidate(user_telegram_id)
            except Exception:
                pass
        await callback.answer("Пользователь удалён", show_alert=True)
        try:
            await callback.message.edit_text("🗑 Пользователь удалён.")
        except TelegramBadRequest:
            pass
        return

    await callback.answer("Неизвестное действие", show_alert=True)


@router.callback_query(F.data == "admin:panel_manager")
async def admin_open_manager_panel(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Вы не администратор.", show_alert=True)
        return
    await callback.message.answer("🛍 Панель менеджера:", reply_markup=get_manager_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "admin:panel_warehouse")
async def admin_open_warehouse_panel(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Вы не администратор.", show_alert=True)
        return
    await callback.message.answer("📦 Панель склада:", reply_markup=get_warehouse_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "admin:panel_courier")
async def admin_open_courier_panel(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Вы не администратор.", show_alert=True)
        return
    await callback.message.answer("🚚 Панель курьера:", reply_markup=get_courier_menu_kb())
    await callback.answer()

@router.callback_query(F.data == "admin:clinics")
async def admin_menu_clinics(callback: types.CallbackQuery, session: AsyncSession):
    """Открыть меню управления клиниками"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Вы не администратор.", show_alert=True)
        return
    
    clinics = await get_all_clinics(session)
    
    if not clinics:
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="➕ Добавить клинику", callback_data="admin:add_clinic")],
            [types.InlineKeyboardButton(text="⬅ В меню", callback_data="admin:back")],
        ])
        await callback.message.edit_text("Нет зарегистрированных клиник. Нажмите «Добавить клинику»:", reply_markup=kb)
    else:
        await callback.message.edit_text("Выберите клинику для редактирования или добавьте новую:", reply_markup=get_clinics_list_kb(clinics))
    await callback.answer()

@router.callback_query(F.data == "admin:back")
async def admin_back_to_menu(callback: types.CallbackQuery):
    """Возврат в главное меню администратора"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Вы не администратор.", show_alert=True)
        return
    await callback.message.edit_text("Выберите действие:", reply_markup=get_admin_menu_kb())
    await callback.answer()

@router.callback_query(F.data == "admin:add_clinic")
async def admin_start_add_clinic(callback: types.CallbackQuery, state: FSMContext):
    """Начать добавление клиники из меню"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Вы не администратор.", show_alert=True)
        return
    await callback.message.edit_text("Введите название клиники:")
    await state.set_state(AddClinicState.waiting_for_name)
    await callback.answer()

@router.callback_query(F.data == "admin:reports")
async def admin_menu_reports(callback: types.CallbackQuery, session: AsyncSession):
    """Генерация отчета"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Вы не администратор.", show_alert=True)
        return
    
    await callback.message.edit_text("Генерация отчета...")
    
    # Fetch all orders with relations (manager, clinic, items)
    stmt = (
        select(Order)
        .options(
            selectinload(Order.clinic),
            selectinload(Order.manager),
            selectinload(Order.items)
        )
        .order_by(Order.created_at.desc())
    )
    result = await session.execute(stmt)
    orders = result.scalars().all()
    
    data = await generate_report_data(orders)
    result = await export_to_sheets(data)
    
    # Check if result is a URL (Google Sheets) or CSV buffer
    if isinstance(result, str):
        # Google Sheets URL
        await callback.message.edit_text(
            f"📊 *Отчет создан в Google Sheets*\n\n"
            f"🔗 [Открыть отчет]({result})\n\n"
            f"Всего заказов: {len(orders)}",
            parse_mode="Markdown",
            reply_markup=get_admin_menu_kb()
        )
    else:
        # XLSX fallback — столбцы и строки разделены, удобно фильтровать
        from aiogram.types import BufferedInputFile
        xlsx_bytes = result.getvalue()
        
        await callback.message.answer_document(
            document=BufferedInputFile(xlsx_bytes, filename="report.xlsx"),
            caption="📊 Отчет по заказам (Excel)\n\nСтолбцы и строки разделены для удобной фильтрации."
        )
        await callback.message.delete()
    
    await callback.answer()

@router.callback_query(F.data == "admin:product_stats")
async def admin_menu_product_stats(callback: types.CallbackQuery, session: AsyncSession, state: FSMContext):
    """Статистика продукции - откроет диалог выбора периода"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Вы не администратор.", show_alert=True)
        return
    
    await state.set_state(ProductStatsState.waiting_for_period)
    
    await callback.message.edit_text(
        "📈 *Статистика продукции*\n\n"
        "Введите период для анализа в формате:\n"
        "ДД.ММ.ГГГГ - ДД.ММ.ГГГГ\n"
        "Например: 01.01.2024 - 31.01.2024\n\n"
        "Или отправьте 'all' для анализа всех заказов",
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(ProductStatsState.waiting_for_period)
async def process_product_stats_period(message: types.Message, session: AsyncSession, state: FSMContext):
    """Обработка ввода периода для статистики"""
    if not is_admin(message.from_user.id):
        return
    
    period_text = message.text.strip().lower()
    
    start_date = None
    end_date = None
    
    if period_text != "all":
        # Парсинг периода
        try:
            parts = period_text.split(" - ")
            if len(parts) == 2:
                start_str = parts[0].strip()
                end_str = parts[1].strip()
                from datetime import datetime
                start_date = datetime.strptime(start_str, "%d.%m.%Y")
                end_date = datetime.strptime(end_str, "%d.%m.%Y")
            else:
                raise ValueError("Неверный формат")
        except Exception as e:
            await message.answer(
                "❌ Неверный формат периода. Используйте формат:\n"
                "ДД.ММ.ГГГГ - ДД.ММ.ГГГГ\n"
                "Или отправьте 'all' для всех заказов"
            )
            return
    
    # Генерация статистики
    await message.answer("Генерация статистики...")
    
    stats = await generate_product_statistics(session, start_date, end_date)
    
    if not stats:
        await message.answer("Нет данных за выбранный период.")
        await state.clear()
        return
    
    # Форматирование для отображения
    formatted_data = await format_product_statistics(stats, limit=20)
    
    # Создание текстового сообщения
    text = "📈 *Статистика продукции*\n\n"
    if start_date and end_date:
        text += f"Период: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}\n\n"
    else:
        text += "Период: Все заказы\n\n"
    
    text += "Топ-20 наиболее заказываемых товаров:\n\n"
    
    for row in formatted_data[1:]:  # Пропускаем заголовок
        place, name, sku, orders, quantity = row
        text += f"{place}. {name} (SKU: {sku})\n"
        text += f"   Заказов: {orders}, Всего: {quantity} шт.\n\n"
    
    # Экспорт в Google Sheets или XLSX
    result = await export_to_sheets(formatted_data, sheet_name="Статистика продукции")
    
    if isinstance(result, str):
        # Google Sheets URL
        await message.answer(
            f"{text}\n"
            f"📊 [Полный отчет в Google Sheets]({result})",
            parse_mode="Markdown",
            reply_markup=get_admin_menu_kb()
        )
    else:
        # XLSX fallback — столбцы и строки разделены
        from aiogram.types import BufferedInputFile
        xlsx_bytes = result.getvalue()
        
        await message.answer(text, parse_mode="Markdown")
        await message.answer_document(
            document=BufferedInputFile(xlsx_bytes, filename="product_stats.xlsx"),
            caption="📊 Статистика продукции (Excel)",
            reply_markup=get_admin_menu_kb()
        )
    
    await state.clear()

@router.message(Command("report"))
async def cmd_report(message: types.Message, session: AsyncSession):
    if not is_admin(message.from_user.id):
        return

    await message.answer("Генерация отчета...")
    
    # Fetch all orders with relations (manager, clinic, items)
    stmt = (
        select(Order)
        .options(
            selectinload(Order.clinic),
            selectinload(Order.manager),
            selectinload(Order.items)
        )
        .order_by(Order.created_at.desc())
    )
    result = await session.execute(stmt)
    orders = result.scalars().all()
    
    data = await generate_report_data(orders)
    result = await export_to_sheets(data)
    
    # Check if result is a URL (Google Sheets) or CSV buffer
    if isinstance(result, str):
        # Google Sheets URL
        await message.answer(
            f"📊 *Отчет создан в Google Sheets*\n\n"
            f"🔗 [Открыть отчет]({result})\n\n"
            f"Всего заказов: {len(orders)}",
            parse_mode="Markdown"
        )
    else:
        # XLSX fallback — столбцы и строки разделены
        from aiogram.types import BufferedInputFile
        xlsx_bytes = result.getvalue()
        
        await message.answer_document(
            document=BufferedInputFile(xlsx_bytes, filename="report.xlsx"),
            caption="📊 Отчет по заказам (Excel)\n\nСтолбцы и строки разделены для удобной фильтрации."
        )
