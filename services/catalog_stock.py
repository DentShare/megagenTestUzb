"""
Временные остатки из каталога (Excel): количество в таблице, вычитание при заказе.
Используется при USE_CATALOG_STOCK=true вместо 1С/mock.
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)

from catalog_config import get_catalog

STOCK_FILE = Path(__file__).resolve().parent.parent / "catalog_stock.json"

# Блокировка для атомарности validate_stock + subtract
_stock_lock = asyncio.Lock()


def _load_store() -> Dict[str, int]:
    if not STOCK_FILE.exists():
        return {}
    try:
        with open(STOCK_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("catalog_stock: failed to load %s: %s", STOCK_FILE, e)
        return {}


def _save_store(store: Dict[str, int]) -> None:
    try:
        with open(STOCK_FILE, "w", encoding="utf-8") as f:
            json.dump(store, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error("catalog_stock: failed to save %s: %s", STOCK_FILE, e)
        raise


def init_from_catalog() -> None:
    """Заполнить store из CATALOG (qty по каждому sku). Перезаписывает существующий файл."""
    CATALOG = get_catalog()
    if not CATALOG:
        logger.warning("catalog_stock: catalog_data not found, skip init")
        return

    store: Dict[str, int] = {}

    def collect(d: dict) -> None:
        if not isinstance(d, dict):
            return
        if "sku" in d and "name" in d:
            sku = d["sku"]
            qty = int(d.get("qty", 0))
            store[sku] = max(0, qty)
            return
        for v in d.values():
            collect(v)

    for cat_data in CATALOG.values():
        if isinstance(cat_data, dict):
            collect(cat_data)

    # no_size lists: line -> no_size (Импланты) или product -> line -> no_size
    def add_no_size(items: list) -> None:
        for item in items:
            if isinstance(item, dict) and "sku" in item:
                sku = item["sku"]
                qty = int(item.get("qty", 0))
                store[sku] = max(0, qty)

    for cat_data in CATALOG.values():
        if not isinstance(cat_data, dict):
            continue
        for top in cat_data.values():
            if not isinstance(top, dict):
                continue
            if "no_size" in top and isinstance(top["no_size"], list):
                add_no_size(top["no_size"])
            for inner in top.values():
                if isinstance(inner, dict) and "no_size" in inner and isinstance(inner["no_size"], list):
                    add_no_size(inner["no_size"])

    _save_store(store)
    logger.info("catalog_stock: init %d SKUs from catalog", len(store))


def ensure_inited() -> None:
    """Если файла нет — инициализировать из каталога."""
    if STOCK_FILE.exists():
        return
    init_from_catalog()


def get_qty(sku: str) -> int:
    ensure_inited()
    store = _load_store()
    return store.get(sku, 0)


def subtract(sku: str, n: int) -> bool:
    """Уменьшить остаток по sku на n. Возвращает True при успехе."""
    ensure_inited()
    store = _load_store()
    cur = store.get(sku, 0)
    if cur < n:
        return False
    store[sku] = cur - n
    _save_store(store)
    return True


def get_stock(product_line: str, diameter: float, diameter_body: float | None = None) -> Dict[float, int]:
    """
    Остатки: (линейка/товар, диаметр) -> { длина или высота_десны: qty }.
    Импланты: line,diameter -> lengths. diameter_body для "4.5 [3.8]" — отдельный продукт.
    """
    ensure_inited()
    CATALOG = get_catalog()
    if not CATALOG:
        return {}

    store = _load_store()
    out: Dict[float, int] = {}

    # Импланты: line -> diameter_key -> length -> product_info (diameter_key: float или (d, body))
    impl = CATALOG.get("Импланты", {})
    if isinstance(impl, dict) and product_line in impl:
        line_data = impl[product_line]
        diam_key = (diameter, diameter_body) if diameter_body is not None else diameter
        diam_data = line_data.get(diam_key) if isinstance(line_data, dict) else None
        if isinstance(diam_data, dict):
            for length, info in diam_data.items():
                if isinstance(length, (int, float)) and isinstance(info, dict) and "sku" in info:
                    out[float(length)] = store.get(info["sku"], 0)
        return out

    # Протетика/Лаборатория: product -> line -> [type ->] diameter -> gum_height -> [height ->] info
    for cat in ("Протетика", "Лаборатория"):
        data = CATALOG.get(cat, {})
        if not isinstance(data, dict) or product_line not in data:
            continue
        prod_data = data[product_line]
        if not isinstance(prod_data, dict):
            continue
        for _line, line_data in prod_data.items():
            if not isinstance(line_data, dict):
                continue
            for top_key, top_val in line_data.items():
                if top_key == "no_size":
                    continue
                diam_data = None
                if top_key in ("прямой", "угловой") and isinstance(top_val, dict):
                    diam_data = top_val.get(diameter)
                elif isinstance(top_key, (int, float)) and top_key == diameter:
                    diam_data = top_val
                if not isinstance(diam_data, dict):
                    continue
                for gumm, rest in diam_data.items():
                    if not isinstance(gumm, (int, float)):
                        continue
                    cur = out.get(float(gumm), 0)
                    if isinstance(rest, dict) and "sku" in rest:
                        cur += store.get(rest["sku"], 0)
                    elif isinstance(rest, dict):
                        for h, info in rest.items():
                            if isinstance(h, (int, float)) and isinstance(info, dict) and "sku" in info:
                                cur += store.get(info["sku"], 0)
                    out[float(gumm)] = cur
        if out:
            return out
    return out


def get_stock_no_size(category: str, line: str) -> Dict[str, int]:
    """Остатки по товарам без размеров: { sku: qty }."""
    ensure_inited()
    CATALOG = get_catalog()
    if not CATALOG:
        return {}

    store = _load_store()
    result: Dict[str, int] = {}

    cat_data = CATALOG.get(category, {})
    if not isinstance(cat_data, dict):
        return result
    # Импланты: line -> no_size
    if category == "Импланты":
        line_data = cat_data.get(line, {})
        if isinstance(line_data, dict):
            no_size = line_data.get("no_size")
            if isinstance(no_size, list):
                for item in no_size:
                    if isinstance(item, dict) and "sku" in item:
                        result[item["sku"]] = store.get(item["sku"], 0)
        return result
    # Остальные: product(=line в UI) -> subline -> no_size или line -> no_size
    top = cat_data.get(line, {})
    if isinstance(top, dict):
        if "no_size" in top and isinstance(top["no_size"], list):
            for item in top["no_size"]:
                if isinstance(item, dict) and "sku" in item:
                    result[item["sku"]] = store.get(item["sku"], 0)
        else:
            for sub, inner in top.items():
                if isinstance(inner, dict) and "no_size" in inner and isinstance(inner["no_size"], list):
                    for item in inner["no_size"]:
                        if isinstance(item, dict) and "sku" in item:
                            result[item["sku"]] = store.get(item["sku"], 0)
    return result
