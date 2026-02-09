import logging
from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from services.db_ops import get_user_by_telegram_id, create_user
from keyboards.admin_kbs import get_role_assignment_kb, get_admin_menu_kb
from keyboards.manager_kbs import get_manager_menu_kb
from keyboards.warehouse_kbs import get_warehouse_menu_kb
from keyboards.courier_kbs import get_courier_menu_kb
from database.models import UserRole

logger = logging.getLogger(__name__)
router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message, session: AsyncSession):
    telegram_id = message.from_user.id
    full_name = message.from_user.full_name
    
    user = await get_user_by_telegram_id(session, telegram_id, use_cache=True)

    # Если пользователь указан в ADMIN_IDS — автоматически делаем его админом
    if telegram_id in config.ADMIN_IDS_LIST:
        from services.cache import user_cache
        if not user:
            user = await create_user(session, telegram_id, full_name, role=UserRole.ADMIN, is_active=True)
            if user_cache is not None:
                try:
                    await user_cache.invalidate(telegram_id)
                except Exception:
                    pass
        else:
            changed = False
            if not user.is_active:
                user.is_active = True
                changed = True
            if user.role != UserRole.ADMIN:
                user.role = UserRole.ADMIN
                changed = True
            if changed:
                await session.commit()
                await session.refresh(user)
                if user_cache is not None:
                    try:
                        await user_cache.invalidate(telegram_id)
                    except Exception:
                        pass

        welcome_text = f"Добро пожаловать, {user.full_name}!\n\nВыберите действие:"
        await message.answer(welcome_text, reply_markup=get_admin_menu_kb())
        return
    
    if not user:
        # User doesn't exist, create inactive user
        user = await create_user(session, telegram_id, full_name)
        # Инвалидируем кеш для нового пользователя
        from services.cache import user_cache
        if user_cache is not None:
            try:
                await user_cache.invalidate(telegram_id)
            except Exception:
                pass
        await message.answer("Ваша заявка на регистрацию принята. Ожидайте подтверждения администратора.")
        
        # Notify Admins
        kb = get_role_assignment_kb(telegram_id)
        for admin_id in config.ADMIN_IDS_LIST:
            try:
                await message.bot.send_message(
                    chat_id=admin_id,
                    text=f"Новый пользователь: {full_name} (ID: {telegram_id})",
                    reply_markup=kb
                )
            except Exception as e:
                # Log error if admin cannot be reached
                logger.error(f"Failed to notify admin {admin_id}: {e}", exc_info=True)
                
    elif not user.is_active:
         await message.answer("Ваш аккаунт ожидает активации.")
    else:
        # Отображение ролевого меню
        welcome_text = f"Добро пожаловать, {user.full_name}!\n\nВыберите действие:"
        
        if user.role == UserRole.ADMIN:
            kb = get_admin_menu_kb()
        elif user.role == UserRole.MANAGER:
            kb = get_manager_menu_kb()
        elif user.role == UserRole.WAREHOUSE:
            kb = get_warehouse_menu_kb()
        elif user.role == UserRole.COURIER:
            kb = get_courier_menu_kb()
        else:
            kb = None
        
        await message.answer(welcome_text, reply_markup=kb)
