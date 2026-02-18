"""
Сервис каталога на базе БД.

Заменяет:
- catalog_data.py (вложенный dict) → SQL-запросы
- catalog_stock.py (JSON-файл остатков) → колонка qty
- catalog_search.py (поиск) → ILIKE / содержит
- one_c.py get_stock → прямой SELECT
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Sequence

from sqlalchemy import select, update, func, distinct, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import CatalogItem

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Навигация: каждый уровень возвращает список уникальных значений
# ---------------------------------------------------------------------------

async def get_categories(session: AsyncSession, active_only: bool = True) -> List[str]:
    """Все категории (Импланты, Протетика, ...)."""
    q = select(distinct(CatalogItem.category)).order_by(CatalogItem.category)
    if active_only:
        q = q.where(CatalogItem.is_active.is_(True))
    result = await session.execute(q)
    return list(result.scalars().all())


async def get_subcategories(
    session: AsyncSession, category: str, active_only: bool = True
) -> List[str]:
    """Подкатегории внутри категории (EzPost, ZrGen, ...)."""
    q = (
        select(distinct(CatalogItem.subcategory))
        .where(CatalogItem.category == category, CatalogItem.subcategory.isnot(None))
        .order_by(CatalogItem.subcategory)
    )
    if active_only:
        q = q.where(CatalogItem.is_active.is_(True))
    result = await session.execute(q)
    return list(result.scalars().all())


async def get_lines(
    session: AsyncSession,
    category: str,
    subcategory: Optional[str] = None,
    active_only: bool = True,
) -> List[str]:
    """Линейки (AnyOne, AnyRidge, ...)."""
    conditions = [CatalogItem.category == category]
    if subcategory is not None:
        conditions.append(CatalogItem.subcategory == subcategory)
    if active_only:
        conditions.append(CatalogItem.is_active.is_(True))
    q = (
        select(distinct(CatalogItem.line))
        .where(*conditions)
        .order_by(CatalogItem.line)
    )
    result = await session.execute(q)
    return list(result.scalars().all())


async def get_product_types(
    session: AsyncSession,
    category: str,
    subcategory: Optional[str] = None,
    line: Optional[str] = None,
    active_only: bool = True,
) -> List[str]:
    """Типы продукта (0, 17, 25, 0 [N], ...). Пустой список если типов нет."""
    conditions = [
        CatalogItem.category == category,
        CatalogItem.product_type.isnot(None),
    ]
    if subcategory is not None:
        conditions.append(CatalogItem.subcategory == subcategory)
    if line is not None:
        conditions.append(CatalogItem.line == line)
    if active_only:
        conditions.append(CatalogItem.is_active.is_(True))
    q = (
        select(distinct(CatalogItem.product_type))
        .where(*conditions)
        .order_by(CatalogItem.product_type)
    )
    result = await session.execute(q)
    return list(result.scalars().all())


async def get_diameters(
    session: AsyncSession,
    category: str,
    line: str,
    subcategory: Optional[str] = None,
    product_type: Optional[str] = None,
    active_only: bool = True,
) -> List[tuple[float, Optional[float]]]:
    """Уникальные (diameter, diameter_body) пары."""
    conditions = [
        CatalogItem.category == category,
        CatalogItem.line == line,
        CatalogItem.diameter.isnot(None),
    ]
    if subcategory is not None:
        conditions.append(CatalogItem.subcategory == subcategory)
    if product_type is not None:
        conditions.append(CatalogItem.product_type == product_type)
    if active_only:
        conditions.append(CatalogItem.is_active.is_(True))
    q = (
        select(CatalogItem.diameter, CatalogItem.diameter_body)
        .where(*conditions)
        .distinct()
        .order_by(CatalogItem.diameter, CatalogItem.diameter_body)
    )
    result = await session.execute(q)
    return list(result.all())


async def get_lengths(
    session: AsyncSession,
    category: str,
    line: str,
    diameter: float,
    diameter_body: Optional[float] = None,
    subcategory: Optional[str] = None,
    product_type: Optional[str] = None,
    active_only: bool = True,
) -> List[dict]:
    """Длины/высоты десны с остатками: [{length, qty, sku, id}]."""
    conditions = [
        CatalogItem.category == category,
        CatalogItem.line == line,
        CatalogItem.diameter == diameter,
        CatalogItem.length.isnot(None),
    ]
    if diameter_body is not None:
        conditions.append(CatalogItem.diameter_body == diameter_body)
    else:
        conditions.append(CatalogItem.diameter_body.is_(None))
    if subcategory is not None:
        conditions.append(CatalogItem.subcategory == subcategory)
    if product_type is not None:
        conditions.append(CatalogItem.product_type == product_type)
    if active_only:
        conditions.append(CatalogItem.is_active.is_(True))
    q = (
        select(CatalogItem)
        .where(*conditions)
        .order_by(CatalogItem.length)
    )
    result = await session.execute(q)
    items = result.scalars().all()
    return [
        {"length": it.length, "qty": it.qty, "sku": it.sku, "id": it.id,
         "name": it.product_name, "height": it.height}
        for it in items
    ]


async def get_heights(
    session: AsyncSession,
    category: str,
    line: str,
    diameter: float,
    length: float,
    diameter_body: Optional[float] = None,
    subcategory: Optional[str] = None,
    product_type: Optional[str] = None,
    active_only: bool = True,
) -> List[dict]:
    """Высоты абатмента с остатками: [{height, qty, sku, id, name}]."""
    conditions = [
        CatalogItem.category == category,
        CatalogItem.line == line,
        CatalogItem.diameter == diameter,
        CatalogItem.length == length,
        CatalogItem.height.isnot(None),
    ]
    if diameter_body is not None:
        conditions.append(CatalogItem.diameter_body == diameter_body)
    else:
        conditions.append(CatalogItem.diameter_body.is_(None))
    if subcategory is not None:
        conditions.append(CatalogItem.subcategory == subcategory)
    if product_type is not None:
        conditions.append(CatalogItem.product_type == product_type)
    if active_only:
        conditions.append(CatalogItem.is_active.is_(True))
    q = (
        select(CatalogItem)
        .where(*conditions)
        .order_by(CatalogItem.height)
    )
    result = await session.execute(q)
    items = result.scalars().all()
    return [
        {"height": it.height, "qty": it.qty, "sku": it.sku, "id": it.id,
         "name": it.product_name}
        for it in items
    ]


async def get_no_size_items(
    session: AsyncSession,
    category: str,
    line: str,
    subcategory: Optional[str] = None,
    active_only: bool = True,
) -> List[dict]:
    """Товары без размеров (diameter IS NULL): [{name, sku, qty, id}]."""
    conditions = [
        CatalogItem.category == category,
        CatalogItem.line == line,
        CatalogItem.diameter.is_(None),
    ]
    if subcategory is not None:
        conditions.append(CatalogItem.subcategory == subcategory)
    if active_only:
        conditions.append(CatalogItem.is_active.is_(True))
    q = (
        select(CatalogItem)
        .where(*conditions)
        .order_by(CatalogItem.product_name)
    )
    result = await session.execute(q)
    items = result.scalars().all()
    return [
        {"name": it.product_name, "sku": it.sku, "qty": it.qty, "id": it.id,
         "unit": it.unit}
        for it in items
    ]


# ---------------------------------------------------------------------------
# Получение товара по ID или SKU
# ---------------------------------------------------------------------------

async def get_item_by_id(session: AsyncSession, item_id: int) -> Optional[CatalogItem]:
    result = await session.execute(
        select(CatalogItem).where(CatalogItem.id == item_id)
    )
    return result.scalar_one_or_none()


async def get_item_by_sku(session: AsyncSession, sku: str) -> Optional[CatalogItem]:
    result = await session.execute(
        select(CatalogItem).where(CatalogItem.sku == sku)
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Остатки (замена catalog_stock.py)
# ---------------------------------------------------------------------------

async def get_qty(session: AsyncSession, sku: str) -> int:
    """Остаток по SKU."""
    result = await session.execute(
        select(CatalogItem.qty).where(CatalogItem.sku == sku)
    )
    val = result.scalar_one_or_none()
    return val if val is not None else 0


async def subtract_qty(session: AsyncSession, sku: str, n: int) -> bool:
    """Атомарное вычитание остатка. Возвращает True при успехе."""
    # WHERE qty >= n гарантирует, что не уйдём в минус
    stmt = (
        update(CatalogItem)
        .where(CatalogItem.sku == sku, CatalogItem.qty >= n)
        .values(qty=CatalogItem.qty - n)
    )
    result = await session.execute(stmt)
    return result.rowcount > 0


async def get_stock_map(
    session: AsyncSession,
    category: str,
    line: str,
    diameter: float,
    diameter_body: Optional[float] = None,
) -> Dict[float, int]:
    """Остатки: {length: qty} — совместимость с one_c.get_stock()."""
    conditions = [
        CatalogItem.category == category,
        CatalogItem.line == line,
        CatalogItem.diameter == diameter,
        CatalogItem.length.isnot(None),
        CatalogItem.is_active.is_(True),
    ]
    if diameter_body is not None:
        conditions.append(CatalogItem.diameter_body == diameter_body)
    else:
        conditions.append(CatalogItem.diameter_body.is_(None))
    q = select(CatalogItem.length, CatalogItem.qty).where(*conditions)
    result = await session.execute(q)
    return {row.length: row.qty for row in result.all()}


# ---------------------------------------------------------------------------
# Поиск (замена catalog_search.py)
# ---------------------------------------------------------------------------

async def search_catalog(
    session: AsyncSession, query: str, limit: int = 15
) -> List[dict]:
    """Поиск по имени или SKU (ILIKE / contains)."""
    if not query or len(query) < 2:
        return []
    pattern = f"%{query}%"
    q = (
        select(CatalogItem)
        .where(
            CatalogItem.is_active.is_(True),
            or_(
                CatalogItem.product_name.ilike(pattern),
                CatalogItem.sku.ilike(pattern),
            ),
        )
        .order_by(CatalogItem.product_name)
        .limit(limit)
    )
    result = await session.execute(q)
    items = result.scalars().all()
    return [
        {
            "id": it.id,
            "name": it.product_name,
            "sku": it.sku,
            "qty": it.qty,
            "category": it.category,
            "line": it.line,
        }
        for it in items
    ]


# ---------------------------------------------------------------------------
# Bulk upsert — загрузка из Excel / синхронизация 1С
# ---------------------------------------------------------------------------

async def upsert_items(
    session: AsyncSession, items: List[dict], deactivate_missing: bool = False
) -> dict:
    """
    Массовый upsert товаров по SKU.

    items: список dict с полями модели CatalogItem (sku обязателен).
    deactivate_missing: если True, товары с SKU не в items помечаются is_active=False.

    Возвращает: {"inserted": N, "updated": N, "deactivated": N}.
    """
    stats = {"inserted": 0, "updated": 0, "deactivated": 0}
    seen_skus = set()

    for data in items:
        sku = data.get("sku")
        if not sku:
            continue
        seen_skus.add(sku)

        existing = await get_item_by_sku(session, sku)
        if existing:
            # Update
            for field in (
                "category", "subcategory", "line", "product_name",
                "product_type", "diameter", "diameter_body",
                "length", "height", "unit", "qty",
                "show_immediately", "is_active",
            ):
                if field in data:
                    setattr(existing, field, data[field])
            stats["updated"] += 1
        else:
            # Insert
            item = CatalogItem(
                sku=sku,
                category=data.get("category", ""),
                subcategory=data.get("subcategory"),
                line=data.get("line", ""),
                product_name=data.get("product_name", ""),
                product_type=data.get("product_type"),
                diameter=data.get("diameter"),
                diameter_body=data.get("diameter_body"),
                length=data.get("length"),
                height=data.get("height"),
                unit=data.get("unit", "шт"),
                qty=data.get("qty", 0),
                show_immediately=data.get("show_immediately", True),
                is_active=data.get("is_active", True),
            )
            session.add(item)
            stats["inserted"] += 1

    if deactivate_missing and seen_skus:
        stmt = (
            update(CatalogItem)
            .where(CatalogItem.sku.notin_(seen_skus), CatalogItem.is_active.is_(True))
            .values(is_active=False)
        )
        result = await session.execute(stmt)
        stats["deactivated"] = result.rowcount

    await session.flush()
    return stats


async def update_stock_batch(
    session: AsyncSession, stock_map: Dict[str, int]
) -> int:
    """
    Пакетное обновление остатков по SKU (для синхронизации с 1С).
    stock_map: {sku: qty}.
    Возвращает количество обновлённых записей.
    """
    updated = 0
    for sku, qty in stock_map.items():
        stmt = (
            update(CatalogItem)
            .where(CatalogItem.sku == sku)
            .values(qty=max(0, qty), synced_at=func.now())
        )
        result = await session.execute(stmt)
        updated += result.rowcount
    await session.flush()
    return updated


# ---------------------------------------------------------------------------
# Визибилити (show_immediately) — агрегация для навигации
# ---------------------------------------------------------------------------

async def get_visibility(
    session: AsyncSession,
    category: str,
    level: str,
    active_only: bool = True,
) -> Dict[str, bool]:
    """
    Видимость элементов на уровне навигации.
    level: 'subcategory' | 'line'
    Возвращает: {name: show_immediately}.
    Если хотя бы один товар в группе имеет show_immediately=True → True.
    """
    if level == "subcategory":
        col = CatalogItem.subcategory
    elif level == "line":
        col = CatalogItem.line
    else:
        return {}

    conditions = [CatalogItem.category == category, col.isnot(None)]
    if active_only:
        conditions.append(CatalogItem.is_active.is_(True))

    q = (
        select(col, func.max(CatalogItem.show_immediately.cast(Integer)))
        .where(*conditions)
        .group_by(col)
    )
    result = await session.execute(q)
    return {name: bool(vis) for name, vis in result.all()}
