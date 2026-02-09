import asyncio
import logging
import sys
import os
import traceback
import time
from pathlib import Path
from logging.handlers import RotatingFileHandler
from aiogram import Bot, Dispatcher
from aiogram.types import ErrorEvent
from aiogram.exceptions import TelegramNetworkError, TelegramServerError, TelegramRetryAfter
from config import config
# Handlers будут импортированы после загрузки каталога
from middlewares.db_middleware import DatabaseMiddleware
from middlewares.logging_middleware import LoggingMiddleware

# Configure logging with rotating file handler
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_name, logging.INFO)
logging.basicConfig(
    level=log_level,
    format=log_format,
    handlers=[
        logging.StreamHandler(sys.stdout),
        RotatingFileHandler(
            'bot.log',
            maxBytes=10*1024*1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )
    ]
)

logger = logging.getLogger(__name__)


_lock_handle = None


def acquire_single_instance_lock() -> None:
    """
    Локальная защита от запуска двух экземпляров бота на одной машине.
    TelegramConflictError чаще всего возникает именно из-за этого.
    """
    global _lock_handle
    lock_path = Path(__file__).resolve().parent / ".bot.lock"
    f = open(lock_path, "a+", encoding="utf-8")
    try:
        if os.name == "nt":
            import msvcrt  # type: ignore
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl  # type: ignore
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except Exception:
        try:
            f.close()
        except Exception:
            pass
        raise RuntimeError(
            "Похоже, бот уже запущен на этой машине (занят .bot.lock). "
            "Остановите другие экземпляры, иначе будет TelegramConflictError."
        )
    _lock_handle = f


def setup_asyncio_exception_logging() -> None:
    """
    Ловит исключения из "фоновых" задач asyncio (Task exception was never retrieved),
    которые не проходят через aiogram handlers/errors.
    """
    loop = asyncio.get_running_loop()

    def _handler(loop: asyncio.AbstractEventLoop, context: dict):
        msg = context.get("message", "asyncio exception")
        exc = context.get("exception")
        logger.error("ASYNCIO %s", msg, exc_info=exc)

    loop.set_exception_handler(_handler)


async def wait_for_db() -> None:
    """
    Ждём БД при старте (чтобы бот не падал из‑за того, что PostgreSQL ещё поднимается).

    Управляется env:
    - DB_WAIT_SECONDS (по умолчанию 60)
    - DB_RETRY_MAX_DELAY (по умолчанию 10)
    """
    max_wait = int(os.getenv("DB_WAIT_SECONDS", "60"))
    max_delay = float(os.getenv("DB_RETRY_MAX_DELAY", "10"))

    from database.core import engine
    from sqlalchemy.exc import OperationalError, SQLAlchemyError
    from sqlalchemy import text

    deadline = time.monotonic() + max_wait
    attempt = 0

    while True:
        attempt += 1
        try:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("✅ Database connection successful")
            return
        except Exception as e:
            # retry только для ошибок подключения/движка, а не для логических ошибок в коде
            retryable = isinstance(e, (OperationalError, SQLAlchemyError, ConnectionRefusedError, OSError)) or (
                e.__class__.__module__.startswith("asyncpg.")
            )
            if not retryable:
                raise
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                # финальный лог как раньше, чтобы было понятно что делать
                logger.error("=" * 60)
                logger.error("❌ ОШИБКА ПОДКЛЮЧЕНИЯ К БАЗЕ ДАННЫХ")
                logger.error("=" * 60)
                logger.error(f"Ошибка: {e}", exc_info=True)
                logger.error("")
                logger.error("Текущие настройки подключения:")
                logger.error(f"  - DB_HOST: {config.DB_HOST}")
                logger.error(f"  - DB_PORT: {config.DB_PORT}")
                logger.error(f"  - DB_NAME: {config.DB_NAME}")
                logger.error(f"  - DB_USER: {config.DB_USER}")
                logger.error("")
                logger.error("Возможные решения:")
                logger.error("1. Убедитесь, что PostgreSQL сервер запущен")
                logger.error("   Windows: Проверьте службу 'postgresql-x64-XX' в 'Службы'")
                logger.error("   Или запустите: net start postgresql-x64-XX")
                logger.error("")
                logger.error("2. Проверьте настройки в файле .env:")
                logger.error("   DB_HOST=localhost (или 127.0.0.1)")
                logger.error("   DB_PORT=5432")
                logger.error("   DB_NAME=megagen_bot")
                logger.error("   DB_USER=postgres")
                logger.error("   DB_PASS=ваш_пароль")
                logger.error("")
                logger.error("3. Проверьте, что база данных создана:")
                logger.error("   Запустите: python init_db.py")
                logger.error("")
                logger.error("4. Проверьте подключение вручную:")
                logger.error("   psql -h localhost -U postgres -d megagen_bot")
                logger.error("=" * 60)
                raise

            delay = min(max_delay, 1.0 * (2 ** min(attempt - 1, 6)))
            delay = min(delay, max(1.0, remaining))
            logger.warning(
                "DB not ready (attempt=%s). Retry in %.1fs (remaining=%.1fs). err=%s",
                attempt,
                delay,
                remaining,
                repr(e),
            )
            await asyncio.sleep(delay)


async def main():
    logger.info("Starting bot...")
    setup_asyncio_exception_logging()
    # Локально предотвращаем запуск двух копий
    acquire_single_instance_lock()
    logger.info("DB_DIALECT=%s DATABASE_URL=%s", getattr(config, "DB_DIALECT", "?"), config.DATABASE_URL)
    
    if not config.BOT_TOKEN:
        logger.error("❌ BOT_TOKEN пустой. Добавьте BOT_TOKEN в .env и перезапустите.")
        raise RuntimeError("BOT_TOKEN is not set")
    
    bot = Bot(token=config.BOT_TOKEN)
    
    # Ждём БД с ретраями (чтобы не падать на старте)
    await wait_for_db()
    
    # Автоматическая синхронизация каталога из Excel при старте
    # ВАЖНО: Делаем это ДО импорта handlers, чтобы они использовали обновленный каталог
    if config.CATALOG_AUTO_SYNC:
        logger.info("📦 Starting catalog auto-sync...")
        try:
            from services.catalog_loader import load_catalog_automatically
            excel_file = config.CATALOG_EXCEL_FILE if config.CATALOG_EXCEL_FILE else None
            if excel_file:
                logger.info(f"Using specified catalog file: {excel_file}")
            result = load_catalog_automatically(excel_file)
            if result:
                logger.info("✅ Catalog auto-sync completed successfully")
            else:
                logger.warning("⚠️ Catalog auto-sync failed or skipped. Using existing catalog_data.py")
        except Exception as e:
            logger.warning(f"Failed to auto-sync catalog: {e}. Using existing catalog_data.py", exc_info=True)
    else:
        logger.info("📦 Catalog auto-sync is disabled (CATALOG_AUTO_SYNC=false). Using existing catalog_data.py")
    
    # Импортируем handlers ПОСЛЕ загрузки каталога
    from handlers import start, admin, manager, warehouse, courier

    # В режиме SQLite всегда поднимаем таблицы автоматически (чтобы проект был "рабочим из коробки")
    if getattr(config, "DB_DIALECT", "postgres") in ("sqlite", "sqlite3"):
        try:
            from database.core import Base, engine
            reset_db = os.getenv("RESET_DB", "").lower() in ("1", "true", "yes")
            if reset_db:
                logger.warning("SQLite mode: RESET_DB enabled -> drop_all + create_all")
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.drop_all)
            logger.info("SQLite mode: ensuring tables exist (create_all)...")
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("SQLite mode: tables are ready")
        except Exception:
            logger.error("SQLite mode: failed to create tables", exc_info=True)
            raise
    
    # Используем Redis для FSM storage, если доступен, иначе MemoryStorage
    redis_client = None
    try:
        import redis.asyncio as redis
        redis_client = redis.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            db=config.REDIS_DB,
            password=config.REDIS_PASSWORD,
            decode_responses=False
        )
        # Проверяем подключение
        await redis_client.ping()
        from aiogram.fsm.storage.redis import RedisStorage
        storage = RedisStorage(redis=redis_client)
        logger.info("Using Redis storage for FSM")
    except Exception as e:
        logger.warning(f"Redis not available, using MemoryStorage: {e}")
        from aiogram.fsm.storage.memory import MemoryStorage
        storage = MemoryStorage()
        redis_client = None
    
    # Инициализируем кеш пользователей
    from services.cache import init_cache
    await init_cache(redis_client)
    
    dp = Dispatcher(storage=storage)
    
    # Логирование всех входящих событий + исключений с контекстом
    dp.message.middleware(LoggingMiddleware(log_success=True))
    dp.callback_query.middleware(LoggingMiddleware(log_success=True))
    
    # Глобальный обработчик ошибок aiogram (ловит необработанные исключения в хендлерах)
    @dp.errors()
    async def global_error_handler(event: ErrorEvent):
        exc = event.exception
        trace = None
        try:
            # update_id помогает искать конкретный апдейт в логах Telegram
            trace = f"update_id={getattr(event.update, 'update_id', None)}"
        except Exception:
            trace = "update_id=?"
        
        logger.error(
            "UNHANDLED %s err=%s",
            trace,
            repr(exc),
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        
        # Пытаемся мягко сообщить пользователю, не раскрывая деталей
        try:
            if event.update and event.update.message:
                await event.update.message.answer("⚠️ Произошла внутренняя ошибка. Мы уже записали её в лог.")
            elif event.update and event.update.callback_query:
                await event.update.callback_query.answer("⚠️ Ошибка. Попробуйте ещё раз.", show_alert=True)
        except Exception:
            # Ничего страшного — главное, что залогировали
            pass
    
    # Добавляем middleware
    dp.message.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(DatabaseMiddleware())
    
    # Rate limiting через Redis или Memory
    from middlewares.rate_limit import create_rate_limit_middleware
    message_rate_limit = await create_rate_limit_middleware(
        redis_client=redis_client,
        max_calls=config.RATE_LIMIT_MESSAGE_MAX,
        period=config.RATE_LIMIT_PERIOD
    )
    callback_rate_limit = await create_rate_limit_middleware(
        redis_client=redis_client,
        max_calls=config.RATE_LIMIT_CALLBACK_MAX,
        period=config.RATE_LIMIT_PERIOD
    )
    dp.message.middleware(message_rate_limit)
    dp.callback_query.middleware(callback_rate_limit)
    
    # Include routers (fallback — последним, ловит необработанные обновления)
    dp.include_router(start.router)
    dp.include_router(admin.router)
    dp.include_router(manager.router)
    dp.include_router(warehouse.router)
    dp.include_router(courier.router)
    from handlers import fallback
    dp.include_router(fallback.router)
    
    try:
        # Удаляем webhook и ждем немного для избежания конфликтов
        # Удаляем webhook и ждем немного для избежания конфликтов
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            logger.info("Webhook deleted successfully")
            await asyncio.sleep(2)  # Задержка для завершения удаления webhook
        except Exception as webhook_error:
            logger.warning(f"Error deleting webhook (may not exist): {webhook_error}")
            # Продолжаем работу даже если webhook не был установлен
        
        logger.info("Bot started successfully")

        # Автоперезапуск polling при временных сетевых сбоях
        restart_delay = float(os.getenv("POLL_RESTART_SECONDS", "5"))
        while True:
            try:
                # Указываем allowed_updates для оптимизации и drop_pending_updates для очистки
                await dp.start_polling(
                    bot,
                    allowed_updates=["message", "callback_query"],
                    drop_pending_updates=True
                )
                break  # нормальная остановка polling
            except TelegramRetryAfter as e:
                # Telegram просит подождать (rate limit)
                wait_s = float(getattr(e, "retry_after", restart_delay))
                logger.warning("TelegramRetryAfter: wait %.1fs then continue", wait_s, exc_info=True)
                await asyncio.sleep(wait_s)
            except (TelegramNetworkError, TelegramServerError, asyncio.TimeoutError, OSError) as e:
                logger.error("Polling crashed (network/server). Restart in %.1fs", restart_delay, exc_info=True)
                await asyncio.sleep(restart_delay)
            except Exception:
                # Неожиданная ошибка — лучше не зацикливаться бесконечно
                raise
    except Exception as e:
        logger.error(f"Error starting bot: {e}", exc_info=True)
        raise
    finally:
        await bot.session.close()
        if 'redis_client' in locals():
            # redis>=5 рекомендует aclose()
            try:
                await redis_client.aclose()
            except Exception:
                await redis_client.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
