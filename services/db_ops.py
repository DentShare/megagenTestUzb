from typing import Any
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from database.models import User, Clinic, UserRole, Order, OrderItem
from services.cache import user_cache

# --- User Services ---

async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int, use_cache: bool = True) -> User | None:
    """Получить пользователя по telegram_id с использованием кеша."""
    # Проверяем кеш (если инициализирован)
    if use_cache and user_cache is not None:
        try:
            cached_user = await user_cache.get(telegram_id)
            if cached_user:
                return cached_user
        except Exception:
            pass  # При ошибке кеша продолжаем с БД
    
    # Запрос к БД
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    # Сохраняем в кеш (если инициализирован)
    if user and use_cache and user_cache is not None:
        try:
            await user_cache.set(telegram_id, user)
        except Exception:
            pass  # При ошибке кеша просто пропускаем
    
    return user

async def create_user(
    session: AsyncSession,
    telegram_id: int,
    full_name: str,
    role: UserRole = UserRole.MANAGER,
    is_active: bool = False,
) -> User:
    """
    Создать пользователя.

    По умолчанию создаётся неактивный пользователь с ролью MANAGER (placeholder),
    чтобы админ мог назначить правильную роль. Для пользователей из ADMIN_IDS
    можно создавать сразу role=ADMIN и is_active=True.
    """
    user = User(
        telegram_id=telegram_id,
        full_name=full_name,
        role=role,
        is_active=is_active,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user

async def approve_user_role(session: AsyncSession, user_id: int, role: UserRole) -> User | None:
    """Активировать пользователя и назначить роль. Инвалидирует кеш."""
    stmt = select(User).where(User.telegram_id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user:
        user.role = role
        user.is_active = True
        await session.commit()
        await session.refresh(user)
        # Инвалидируем кеш при изменении данных пользователя (если инициализирован)
        if user_cache is not None:
            try:
                await user_cache.invalidate(user_id)
            except Exception:
                pass  # При ошибке кеша просто пропускаем
    
    return user

# --- Clinic Services ---

async def create_clinic(session: AsyncSession, name: str, doctor_name: str, 
                        address: str, geo_lat: float, geo_lon: float, 
                        chat_id: int | None = None, phone_number: str = None) -> Clinic:
    """Создать клинику. chat_id можно не указывать — добавить позже при редактировании."""
    nav_link = f"https://www.google.com/maps/search/?api=1&query={geo_lat},{geo_lon}"
    
    clinic = Clinic(
        name=name,
        doctor_name=doctor_name,
        address=address,
        geo_lat=geo_lat,
        geo_lon=geo_lon,
        telegram_chat_id=chat_id,
        phone_number=phone_number,
        navigator_link=nav_link
    )
    session.add(clinic)
    await session.commit()
    await session.refresh(clinic)
    return clinic

async def get_clinic_by_id(session: AsyncSession, clinic_id: int) -> Clinic | None:
    stmt = select(Clinic).where(Clinic.id == clinic_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def get_all_clinics(session: AsyncSession) -> list[Clinic]:
    stmt = select(Clinic).order_by(Clinic.name)
    result = await session.execute(stmt)
    return list(result.scalars().all())

async def update_clinic_field(session: AsyncSession, clinic_id: int, field: str, value: Any) -> Clinic | None:
    clinic = await get_clinic_by_id(session, clinic_id)
    if not clinic:
        return None
    
    if field == "name":
        clinic.name = value
    elif field == "doctor_name":
        clinic.doctor_name = value
    elif field == "phone_number":
        clinic.phone_number = value
    elif field == "address":
        clinic.address = value
    elif field == "geo_lat":
        clinic.geo_lat = value
        # Update navigator link when location changes
        clinic.navigator_link = f"https://www.google.com/maps/search/?api=1&query={value},{clinic.geo_lon}"
    elif field == "geo_lon":
        clinic.geo_lon = value
        # Update navigator link when location changes
        clinic.navigator_link = f"https://www.google.com/maps/search/?api=1&query={clinic.geo_lat},{value}"
    elif field == "telegram_chat_id":
        clinic.telegram_chat_id = value
    
    await session.commit()
    await session.refresh(clinic)
    return clinic

# --- Order Services ---

async def get_order_with_relations(session: AsyncSession, order_id: int) -> Order | None:
    """Получить заказ со всеми связанными данными (eager loading)."""
    stmt = (
        select(Order)
        .options(
            selectinload(Order.items),
            joinedload(Order.clinic),
            joinedload(Order.manager),
            joinedload(Order.courier)
        )
        .where(Order.id == order_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()