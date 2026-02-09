"""
Скрипт для проверки подключения к базе данных.

Поддержка:
- PostgreSQL (postgresql+asyncpg)
- SQLite (sqlite+aiosqlite)

Использование: python check_db.py
"""
import asyncio
import sys
from config import config
from database.core import engine, session_maker
from sqlalchemy import text, inspect
from sqlalchemy.exc import OperationalError
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


async def check_connection():
    """Проверка подключения к базе данных"""
    print("=" * 60)
    print("Проверка подключения к базе данных")
    print("=" * 60)
    print(f"Dialect: {getattr(config, 'DB_DIALECT', 'postgres')}")
    print(f"Host: {config.DB_HOST}")
    print(f"Port: {config.DB_PORT}")
    print(f"Database: {config.DB_NAME}")
    print(f"User: {config.DB_USER}")
    print("-" * 60)
    
    try:
        # Проверка подключения
        print("1. Проверка подключения...", end=" ")
        async with engine.begin() as conn:
            if getattr(config, "DB_DIALECT", "postgres") in ("sqlite", "sqlite3"):
                result = await conn.execute(text("SELECT sqlite_version()"))
            else:
                result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print("✅ Успешно!")
            if version:
                print(f"   Версия: {str(version).split(',')[0]}")
    except ConnectionRefusedError:
        print("❌ ОШИБКА!")
        if getattr(config, "DB_DIALECT", "postgres") in ("sqlite", "sqlite3"):
            print("   SQLite файл недоступен или ошибка открытия")
            print("   Решение: проверьте SQLITE_PATH и права на файл")
        else:
            print("   PostgreSQL сервер не запущен или недоступен")
            print("   Решение: Запустите PostgreSQL сервер")
        return False
    except OperationalError as e:
        print("❌ ОШИБКА!")
        print(f"   {e}")
        if "password" in str(e).lower() or "authentication" in str(e).lower():
            print("   Проблема с аутентификацией")
            print("   Решение: Проверьте DB_USER и DB_PASS в .env файле")
        elif "database" in str(e).lower() and "does not exist" in str(e).lower():
            print("   База данных не существует")
            print("   Решение: Запустите 'python init_db.py' для создания БД")
        return False
    except Exception as e:
        print("❌ ОШИБКА!")
        print(f"   Неожиданная ошибка: {e}")
        return False
    
    try:
        # Проверка существования таблиц
        print("\n2. Проверка таблиц...", end=" ")
        async with session_maker() as session:
            inspector = inspect(engine.sync_engine)
            tables = inspector.get_table_names()
            if tables:
                print(f"✅ Найдено таблиц: {len(tables)}")
                print(f"   Таблицы: {', '.join(tables)}")
            else:
                print("⚠️  Таблицы не найдены")
                print("   Решение: Запустите 'python init_db.py' для создания таблиц")
    except Exception as e:
        print(f"⚠️  Ошибка при проверке таблиц: {e}")
    
    try:
        # Проверка данных
        print("\n3. Проверка данных...", end=" ")
        async with session_maker() as session:
            from database.models import User, Order, Clinic
            
            user_count = await session.execute(text("SELECT COUNT(*) FROM users"))
            order_count = await session.execute(text("SELECT COUNT(*) FROM orders"))
            clinic_count = await session.execute(text("SELECT COUNT(*) FROM clinics"))
            
            print("✅")
            print(f"   Пользователей: {user_count.scalar()}")
            print(f"   Заказов: {order_count.scalar()}")
            print(f"   Клиник: {clinic_count.scalar()}")
    except Exception as e:
        print(f"⚠️  Ошибка при проверке данных: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Все проверки пройдены успешно!")
    print("=" * 60)
    return True


async def main():
    """Главная функция"""
    success = await check_connection()
    if not success:
        print("\n💡 Полезные команды:")
        print("   - Запуск PostgreSQL (Windows): net start postgresql-x64-XX")
        print("   - Создание БД: python init_db.py")
        print("   - Проверка службы: services.msc (найти PostgreSQL)")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)
