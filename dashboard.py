"""
Веб-дашборд для мониторинга системы Megagen Bot
Запуск: uvicorn dashboard:app --host 0.0.0.0 --port 8000 --reload
"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
import json
from pathlib import Path

from config import config
from database.core import session_maker
from database.models import User, Order, OrderItem, Clinic, OrderStatus, UserRole, DeliveryType

# Создаем FastAPI приложение
app = FastAPI(title="Megagen Bot Dashboard")

# Настройка шаблонов
templates_dir = Path(__file__).parent / "templates"
templates_dir.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=str(templates_dir))


async def get_db():
    """Dependency для получения сессии БД"""
    async with session_maker() as session:
        yield session


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Главная страница дашборда"""
    async with session_maker() as session:
        # Статистика по заказам
        total_orders = await session.scalar(select(func.count(Order.id)))
        new_orders = await session.scalar(
            select(func.count(Order.id)).where(Order.status == OrderStatus.NEW)
        )
        assembly_orders = await session.scalar(
            select(func.count(Order.id)).where(Order.status == OrderStatus.ASSEMBLY)
        )
        delivering_orders = await session.scalar(
            select(func.count(Order.id)).where(Order.status == OrderStatus.DELIVERING)
        )
        delivered_today = await session.scalar(
            select(func.count(Order.id)).where(
                Order.status == OrderStatus.DELIVERED,
                Order.delivered_at >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            )
        )
        
        # Статистика по пользователям
        total_users = await session.scalar(select(func.count(User.id)))
        active_users = await session.scalar(
            select(func.count(User.id)).where(User.is_active == True)
        )
        
        # Статистика по клиникам
        total_clinics = await session.scalar(select(func.count(Clinic.id)))
        
        # Последние заказы
        recent_orders_result = await session.execute(
            select(Order, User.full_name.label("manager_name"), Clinic.name.label("clinic_name"))
            .join(User, Order.manager_id == User.id)
            .join(Clinic, Order.clinic_id == Clinic.id)
            .order_by(Order.created_at.desc())
            .limit(10)
        )
        recent_orders_list = []
        for order, manager_name, clinic_name in recent_orders_result:
            recent_orders_list.append({
                "id": order.id,
                "status": order.status.value,
                "manager": manager_name,
                "clinic": clinic_name,
                "is_urgent": order.is_urgent,
                "delivery_type": order.delivery_type.value,
                "created_at": order.created_at.strftime("%Y-%m-%d %H:%M:%S") if order.created_at else None,
            })
        
        # Статистика по статусам
        status_stats_result = await session.execute(
            select(Order.status, func.count(Order.id).label("count"))
            .group_by(Order.status)
        )
        status_data = {status.value: count for status, count in status_stats_result}
        
        # Заказы за последние 7 дней
        week_ago = datetime.now() - timedelta(days=7)
        orders_by_day_result = await session.execute(
            select(
                func.date(Order.created_at).label("date"),
                func.count(Order.id).label("count")
            )
            .where(Order.created_at >= week_ago)
            .group_by(func.date(Order.created_at))
            .order_by(func.date(Order.created_at))
        )
        daily_stats = {}
        for date, count in orders_by_day_result:
            daily_stats[str(date)] = count
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "total_orders": total_orders or 0,
            "new_orders": new_orders or 0,
            "assembly_orders": assembly_orders or 0,
            "delivering_orders": delivering_orders or 0,
            "delivered_today": delivered_today or 0,
            "total_users": total_users or 0,
            "active_users": active_users or 0,
            "total_clinics": total_clinics or 0,
            "recent_orders": recent_orders_list,
            "status_stats": json.dumps(status_data),
            "daily_stats": json.dumps(daily_stats),
        })


@app.get("/api/stats")
async def get_stats():
    """API endpoint для получения статистики"""
    async with session_maker() as session:
        stats = {
            "orders": {
                "total": await session.scalar(select(func.count(Order.id))) or 0,
                "new": await session.scalar(
                    select(func.count(Order.id)).where(Order.status == OrderStatus.NEW)
                ) or 0,
                "assembly": await session.scalar(
                    select(func.count(Order.id)).where(Order.status == OrderStatus.ASSEMBLY)
                ) or 0,
                "delivering": await session.scalar(
                    select(func.count(Order.id)).where(Order.status == OrderStatus.DELIVERING)
                ) or 0,
                "delivered": await session.scalar(
                    select(func.count(Order.id)).where(Order.status == OrderStatus.DELIVERED)
                ) or 0,
            },
            "users": {
                "total": await session.scalar(select(func.count(User.id))) or 0,
                "active": await session.scalar(
                    select(func.count(User.id)).where(User.is_active == True)
                ) or 0,
            },
            "clinics": {
                "total": await session.scalar(select(func.count(Clinic.id))) or 0,
            }
        }
        return stats


@app.get("/api/orders")
async def get_orders(limit: int = 50, status: str = None):
    """API endpoint для получения списка заказов"""
    async with session_maker() as session:
        query = (
            select(Order, User.full_name.label("manager_name"), Clinic.name.label("clinic_name"))
            .join(User, Order.manager_id == User.id)
            .join(Clinic, Order.clinic_id == Clinic.id)
            .order_by(Order.created_at.desc())
            .limit(limit)
        )
        
        if status:
            try:
                status_enum = OrderStatus[status.upper()]
                query = query.where(Order.status == status_enum)
            except KeyError:
                pass
        
        orders_result = await session.execute(query)
        result = []
        for order, manager_name, clinic_name in orders_result:
            result.append({
                "id": order.id,
                "status": order.status.value,
                "manager": manager_name,
                "clinic": clinic_name,
                "is_urgent": order.is_urgent,
                "delivery_type": order.delivery_type.value,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
            })
        return {"orders": result}


@app.get("/api/users")
async def get_users():
    """API endpoint для получения списка пользователей"""
    async with session_maker() as session:
        users_result = await session.execute(select(User))
        result = []
        for user in users_result.scalars():
            result.append({
                "id": user.id,
                "telegram_id": user.telegram_id,
                "full_name": user.full_name,
                "role": user.role.value,
                "is_active": user.is_active,
            })
        return {"users": result}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
