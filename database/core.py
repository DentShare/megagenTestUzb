import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from config import config

class Base(DeclarativeBase):
    pass

# Отключаем echo в продакшене, включаем только в debug режиме
debug_mode = os.getenv("DEBUG", "False").lower() == "true"

engine_kwargs = {
    "echo": debug_mode,
    "pool_pre_ping": True,
}

# Для SQLite не используем настройки пула PostgreSQL
if config.DB_DIALECT in ("sqlite", "sqlite3"):
    engine_kwargs.update(
        {
            "poolclass": NullPool,
            "connect_args": {"check_same_thread": False},
        }
    )
else:
    engine_kwargs.update(
        {
            "pool_size": config.DB_POOL_SIZE,
            "max_overflow": config.DB_MAX_OVERFLOW,
            "pool_recycle": 3600,
        }
    )

engine = create_async_engine(config.DATABASE_URL, **engine_kwargs)

session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

async def get_session() -> AsyncSession:
    """Генератор сессий (для обратной совместимости)."""
    async with session_maker() as session:
        yield session
