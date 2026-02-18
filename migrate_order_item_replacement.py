"""
Миграция: добавить в order_items поля для замены товара (need_replacement, replacement_sku, replacement_name).
Запуск: python migrate_order_item_replacement.py
"""
import asyncio
import logging
from sqlalchemy import text
from database.core import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate():
    async with engine.begin() as conn:
        dialect_name = conn.dialect.name
        if dialect_name == "sqlite":
            for col, defn in [
                ("need_replacement", "BOOLEAN DEFAULT 0 NOT NULL"),
                ("replacement_sku", "TEXT"),
                ("replacement_name", "TEXT"),
            ]:
                try:
                    await conn.execute(text(f"ALTER TABLE order_items ADD COLUMN {col} {defn}"))
                    logger.info("Added column order_items.%s", col)
                except Exception as e:
                    if "duplicate column" in str(e).lower():
                        logger.info("Column order_items.%s already exists, skip", col)
                    else:
                        raise
        else:
            # PostgreSQL
            for col, defn in [
                ("need_replacement", "BOOLEAN DEFAULT FALSE NOT NULL"),
                ("replacement_sku", "VARCHAR"),
                ("replacement_name", "VARCHAR"),
            ]:
                try:
                    await conn.execute(text(f"ALTER TABLE order_items ADD COLUMN IF NOT EXISTS {col} {defn}"))
                    logger.info("Added column order_items.%s", col)
                except Exception as e:
                    logger.warning("Column order_items.%s: %s", col, e)
    await engine.dispose()
    logger.info("Migration done.")


if __name__ == "__main__":
    asyncio.run(migrate())
