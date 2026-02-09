import asyncio
import logging

from database.core import engine, Base
from database.models import User, Clinic, Order, OrderItem
# Importing models ensures they are registered with Base.metadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_db():
    async with engine.begin() as conn:
        # Create all tables
        # In production, you would use Alembic for migrations.
        # This script is for initial setup.
        logger.info("Creating tables...")
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Tables created successfully.")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_db())
