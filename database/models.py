import enum
from datetime import datetime
from typing import Optional, List

from sqlalchemy import BigInteger, Integer, String, Boolean, ForeignKey, DateTime, Float, Enum as PgEnum, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.core import Base
from config import config


# В SQLite автоинкремент корректно работает только для PRIMARY KEY типа INTEGER (rowid).
# Поэтому в dev/test режиме на SQLite используем Integer для PK, а в Postgres оставляем BigInteger.
PK_INT = Integer if config.DB_DIALECT in ("sqlite", "sqlite3") else BigInteger

# --- Enums ---
class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    WAREHOUSE = "warehouse"
    COURIER = "courier"

class OrderStatus(str, enum.Enum):
    NEW = "new"
    ASSEMBLY = "assembly"
    READY_FOR_PICKUP = "ready_for_pickup"
    DELIVERING = "delivering"
    DELIVERED = "delivered"
    CANCELED = "canceled"

class DeliveryType(str, enum.Enum):
    COURIER = "courier"
    TAXI = "taxi"

# --- Models ---

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(PK_INT, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[UserRole] = mapped_column(PgEnum(UserRole, name="user_role_enum"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships (Optional but good for navigation)
    # orders_as_manager = relationship("Order", back_populates="manager", foreign_keys="Order.manager_id")
    # orders_as_courier = relationship("Order", back_populates="courier", foreign_keys="Order.courier_id")
    
    __table_args__ = (
        {"comment": "Пользователи системы"},
    )


class Clinic(Base):
    __tablename__ = "clinics"

    id: Mapped[int] = mapped_column(PK_INT, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    doctor_name: Mapped[str] = mapped_column(String, nullable=False)
    telegram_chat_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True) # For notifications
    address: Mapped[str] = mapped_column(String, nullable=False)
    geo_lat: Mapped[float] = mapped_column(Float, nullable=False)
    geo_lon: Mapped[float] = mapped_column(Float, nullable=False)
    phone_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    navigator_link: Mapped[str] = mapped_column(String, nullable=False)
    
    __table_args__ = (
        {"comment": "Клиники"},
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(PK_INT, primary_key=True, autoincrement=True)
    
    manager_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    courier_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.id"), nullable=False, index=True)
    
    status: Mapped[OrderStatus] = mapped_column(PgEnum(OrderStatus, name="order_status_enum"), default=OrderStatus.NEW, nullable=False, index=True)
    is_urgent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    delivery_type: Mapped[DeliveryType] = mapped_column(PgEnum(DeliveryType, name="delivery_type_enum"), nullable=False)
    taxi_link: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    assembled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    manager: Mapped["User"] = relationship("User", foreign_keys=[manager_id])
    courier: Mapped[Optional["User"]] = relationship("User", foreign_keys=[courier_id])
    clinic: Mapped["Clinic"] = relationship("Clinic")
    items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    
    __table_args__ = (
        {"comment": "Заказы"},
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(PK_INT, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    # Note: Requirements specify 'sku', but using 'item_sku' to avoid conflicts with Python's built-in
    # The field is correctly mapped in handlers (item['sku'] -> item_sku)
    item_sku: Mapped[str] = mapped_column(String, nullable=False)
    item_name: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    # Замена товара (склад указал «нет в наличии», менеджер подобрал замену)
    need_replacement: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    replacement_sku: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    replacement_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    order: Mapped["Order"] = relationship("Order", back_populates="items")


class CatalogItem(Base):
    """Плоская таблица каталога — единый источник товаров, остатков, навигации."""
    __tablename__ = "catalog_items"

    id: Mapped[int] = mapped_column(PK_INT, primary_key=True, autoincrement=True)

    # Иерархия навигации
    category: Mapped[str] = mapped_column(String, nullable=False, index=True)
    subcategory: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    line: Mapped[str] = mapped_column(String, nullable=False, index=True)
    product_name: Mapped[str] = mapped_column(String, nullable=False)

    # Параметры (nullable для товаров без размеров)
    product_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    diameter: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    diameter_body: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    length: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    height: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Товарные данные
    sku: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    unit: Mapped[str] = mapped_column(String, nullable=False, default="шт")
    qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Отображение
    show_immediately: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Синхронизация с 1С
    synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_catalog_nav", "category", "subcategory", "line"),
        Index("ix_catalog_params", "category", "line", "diameter", "length"),
        {"comment": "Каталог товаров"},
    )
