"""
Поиск по каталогу продукции (название, артикул) для подбора замены товара.
"""
from typing import List, Dict, Any


def _flatten_catalog(catalog: Any, out: List[Dict[str, str]]) -> None:
    """Рекурсивно собирает все позиции с name и sku из CATALOG."""
    if isinstance(catalog, dict):
        if "name" in catalog and "sku" in catalog:
            out.append({"name": catalog["name"], "sku": catalog["sku"]})
        for v in catalog.values():
            _flatten_catalog(v, out)
    elif isinstance(catalog, list):
        for x in catalog:
            if isinstance(x, dict) and "name" in x and "sku" in x:
                out.append({"name": x["name"], "sku": x["sku"]})


def search_catalog(query: str, limit: int = 15) -> List[Dict[str, str]]:
    """
    Поиск по каталогу по названию или артикулу (без учёта регистра).
    Возвращает список {name, sku}, не более limit элементов.
    """
    try:
        from catalog_data import CATALOG
    except ImportError:
        return []
    flat: List[Dict[str, str]] = []
    _flatten_catalog(CATALOG, flat)
    q = (query or "").strip().lower()
    if not q:
        return flat[:limit]
    matched = []
    for item in flat:
        name = (item.get("name") or "").lower()
        sku = (item.get("sku") or "").lower()
        if q in name or q in sku:
            matched.append(item)
    return matched[:limit]
