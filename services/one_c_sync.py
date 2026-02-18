"""
Синхронизация каталога с 1С.

Два режима:
1. Polling — бот периодически запрашивает остатки из 1С API
2. Webhook — 1С пушит обновления (вызывается из aiohttp handler)

Конфигурация в .env:
    ONE_C_MODE=real          # включить реальную синхронизацию
    ONE_C_API_URL=https://1c.example.com/api
    ONE_C_USERNAME=bot
    ONE_C_PASSWORD=secret
    ONE_C_TIMEOUT=30
    ONE_C_SYNC_INTERVAL=300  # секунд между polling-запросами
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from services.catalog_db import update_stock_batch, get_item_by_sku

logger = logging.getLogger(__name__)

# Фоновая задача polling (для отмены при shutdown)
_sync_task: Optional[asyncio.Task] = None


# ---------------------------------------------------------------------------
# 1С API Client
# ---------------------------------------------------------------------------

class OneCClient:
    """HTTP-клиент для 1С REST API."""

    def __init__(self):
        self.base_url = config.ONE_C_API_URL.rstrip("/")
        self.auth = aiohttp.BasicAuth(config.ONE_C_USERNAME, config.ONE_C_PASSWORD)
        self.timeout = aiohttp.ClientTimeout(total=config.ONE_C_TIMEOUT)

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self.base_url}{path}"
        try:
            async with aiohttp.ClientSession(
                auth=self.auth, timeout=self.timeout
            ) as session:
                async with session.request(method, url, **kwargs) as resp:
                    resp.raise_for_status()
                    return await resp.json()
        except aiohttp.ClientError as e:
            logger.error("1C API error [%s %s]: %s", method, path, e)
            raise

    async def get_stock_all(self) -> Dict[str, int]:
        """
        Получить все остатки из 1С.
        Ожидаемый формат ответа: {"items": [{"sku": "AR-3507", "qty": 50}, ...]}
        """
        data = await self._request("GET", "/stock")
        items = data.get("items", [])
        return {item["sku"]: item.get("qty", 0) for item in items if "sku" in item}

    async def get_stock_updated(self, since: datetime) -> Dict[str, int]:
        """
        Получить остатки, изменённые с указанного момента.
        Ожидаемый формат: {"items": [{"sku": ..., "qty": ...}, ...]}
        """
        params = {"updated_since": since.isoformat()}
        data = await self._request("GET", "/stock", params=params)
        items = data.get("items", [])
        return {item["sku"]: item.get("qty", 0) for item in items if "sku" in item}

    async def get_stock_by_skus(self, skus: List[str]) -> Dict[str, int]:
        """
        Получить остатки по списку SKU.
        POST /stock/batch {"skus": ["AR-3507", "AR-3508"]}
        Ответ: {"items": [{"sku": "AR-3507", "qty": 50}, ...]}
        """
        data = await self._request("POST", "/stock/batch", json={"skus": skus})
        items = data.get("items", [])
        return {item["sku"]: item.get("qty", 0) for item in items if "sku" in item}

    async def send_order(self, order_data: dict) -> dict:
        """
        Отправить заказ в 1С.
        POST /orders {"order_id": 123, "items": [{"sku": ..., "qty": ...}]}
        Ответ: {"success": true, "1c_order_id": "..."}
        """
        return await self._request("POST", "/orders", json=order_data)


# Singleton
_client: Optional[OneCClient] = None


def get_client() -> OneCClient:
    global _client
    if _client is None:
        _client = OneCClient()
    return _client


# ---------------------------------------------------------------------------
# Polling: периодическая синхронизация остатков
# ---------------------------------------------------------------------------

async def sync_stock(session: AsyncSession) -> int:
    """
    Один цикл синхронизации: запросить остатки из 1С → обновить в БД.
    Возвращает количество обновлённых записей.
    """
    client = get_client()
    try:
        stock = await client.get_stock_all()
        if not stock:
            logger.info("1C sync: no stock data received")
            return 0
        updated = await update_stock_batch(session, stock)
        await session.commit()
        logger.info("1C sync: updated %d items", updated)
        return updated
    except Exception as e:
        logger.error("1C sync error: %s", e, exc_info=True)
        await session.rollback()
        return 0


async def _polling_loop(session_maker, interval: int):
    """Фоновый цикл polling."""
    logger.info("1C polling started (interval=%ds)", interval)
    while True:
        try:
            async with session_maker() as session:
                await sync_stock(session)
        except asyncio.CancelledError:
            logger.info("1C polling stopped")
            return
        except Exception as e:
            logger.error("1C polling iteration error: %s", e)
        await asyncio.sleep(interval)


def start_polling(session_maker, interval: int = 300):
    """Запуск фонового polling (вызывать из main.py)."""
    global _sync_task
    if config.ONE_C_IS_TEST_MODE:
        logger.info("1C in test mode — polling disabled")
        return
    if not config.ONE_C_API_URL:
        logger.warning("ONE_C_API_URL not set — polling disabled")
        return
    _sync_task = asyncio.create_task(_polling_loop(session_maker, interval))


def stop_polling():
    """Остановка polling (при shutdown)."""
    global _sync_task
    if _sync_task and not _sync_task.done():
        _sync_task.cancel()
        _sync_task = None


# ---------------------------------------------------------------------------
# Webhook: 1С пушит обновления
# ---------------------------------------------------------------------------

async def handle_stock_webhook(session: AsyncSession, payload: dict) -> dict:
    """
    Обработка webhook от 1С.

    Ожидаемый payload:
        {"items": [{"sku": "AR-3507", "qty": 50}, ...]}

    Возвращает: {"updated": N, "unknown_skus": [...]}
    """
    items = payload.get("items", [])
    if not items:
        return {"updated": 0, "unknown_skus": []}

    stock_map = {}
    unknown = []
    for item in items:
        sku = item.get("sku")
        if not sku:
            continue
        existing = await get_item_by_sku(session, sku)
        if existing:
            stock_map[sku] = item.get("qty", 0)
        else:
            unknown.append(sku)

    updated = 0
    if stock_map:
        updated = await update_stock_batch(session, stock_map)
        await session.commit()

    if unknown:
        logger.warning("1C webhook: unknown SKUs: %s", unknown)

    return {"updated": updated, "unknown_skus": unknown}


# ---------------------------------------------------------------------------
# Совместимость: замена one_c.get_stock()
# ---------------------------------------------------------------------------

async def get_stock(
    session: AsyncSession,
    product_line: str,
    diameter: float,
    diameter_body: Optional[float] = None,
) -> Dict[float, int]:
    """
    Получение остатков — совместимая замена one_c.get_stock().
    Читает из catalog_items (БД), а не из 1С напрямую.
    1С синхронизирует catalog_items через polling/webhook.
    """
    from services.catalog_db import get_stock_map
    return await get_stock_map(session, "Импланты", product_line, diameter, diameter_body)
