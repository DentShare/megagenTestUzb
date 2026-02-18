"""
Authentication and authorization middleware for role-based access control.
"""
import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from services.db_ops import get_user_by_telegram_id
from services.cache import user_cache
from database.models import UserRole
from config import config

logger = logging.getLogger(__name__)


class RoleRequiredMiddleware(BaseMiddleware):
    """
    Middleware that checks if user has required role and is active.
    Can be applied to specific routers or handlers.
    """
    
    def __init__(self, required_role: UserRole | None = None, admin_allowed: bool = False):
        """
        Args:
            required_role: Required user role. If None, only checks if user is active.
            admin_allowed: If True, admins can access regardless of role.
        """
        self.required_role = required_role
        self.admin_allowed = admin_allowed
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Extract user ID from event
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None
        
        if not user_id:
            logger.warning("No user ID found in event")
            return await handler(event, data)
        
        # Check if user is admin (admins bypass role checks if admin_allowed=True)
        is_admin = user_id in config.ADMIN_IDS
        if self.admin_allowed and is_admin:
            return await handler(event, data)
        
        # Получаем сессию из data (должна быть добавлена DatabaseMiddleware)
        session: AsyncSession = data.get('session')
        if not session:
            logger.error("Session not found in data. DatabaseMiddleware must be registered.")
            return await handler(event, data)
        
        # Check user role and active status (с использованием кеша)
        user = await get_user_by_telegram_id(session, user_id, use_cache=True)
        
        if not user:
            logger.warning("User %s not found in database", user_id)
            if isinstance(event, CallbackQuery):
                await event.answer("❌ Пользователь не найден в системе.", show_alert=True)
            return
        
        if not user.is_active:
            logger.warning("User %s is not active", user_id)
            if isinstance(event, CallbackQuery):
                await event.answer("❌ Ваш аккаунт не активирован.", show_alert=True)
            elif isinstance(event, Message):
                await event.answer("❌ Ваш аккаунт не активирован. Ожидайте подтверждения администратора.")
            return
        
        # Check role if required
        if self.required_role and user.role != self.required_role:
            logger.warning("User %s (role: %s) attempted to access %s resource", user_id, user.role, self.required_role)
            if isinstance(event, CallbackQuery):
                await event.answer(f"❌ Доступ запрещен. Требуется роль: {self.required_role.value}", show_alert=True)
            elif isinstance(event, Message):
                await event.answer(f"❌ Доступ запрещен. Требуется роль: {self.required_role.value}")
            return
        
        # Store user in data for handler access
        data['user'] = user
        return await handler(event, data)


def create_role_filter(required_role: UserRole, admin_allowed: bool = False):
    """
    Factory function to create a filter for specific role.
    Usage in router:
        router.message.register(handler, RoleFilter(UserRole.MANAGER))
    """
    from aiogram.filters import BaseFilter
    
    class RoleFilter(BaseFilter):
        async def __call__(self, obj: TelegramObject, *args) -> bool:
            user_id = None
            if isinstance(obj, Message):
                user_id = obj.from_user.id if obj.from_user else None
            elif isinstance(obj, CallbackQuery):
                user_id = obj.from_user.id if obj.from_user else None
            
            if not user_id:
                return False
            
            # Admins bypass if allowed
            if admin_allowed and user_id in config.ADMIN_IDS_LIST:
                return True
            
            # Note: This filter should be used with DatabaseMiddleware
            # Session should be in data, but for filters we might need to get it differently
            # For now, keeping the old approach but with cache
            from database.core import session_maker
            async with session_maker() as session:
                user = await get_user_by_telegram_id(session, user_id, use_cache=True)
                if not user or not user.is_active:
                    return False
                if user.role == required_role:
                    return True
                return False
    
    return RoleFilter()

