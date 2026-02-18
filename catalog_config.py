"""
Конфигурация каталога: маппинг Excel → навигация в боте.

Настройте здесь:
- Какие колонки Excel соответствуют каким полям
- Структура навигации для каждой категории
- Правила различения типа (угол) и диаметра
"""

# --- Маппинг колонок Excel ---
# Ключевые слова для поиска колонок по заголовкам (регистр не важен)
EXCEL_COLUMN_KEYWORDS = {
    "category": ["категория", "category", "подкатегория", "subcategory", "вид", "тип товара", "кат", "cat"],
    "line": ["линейка", "line", "серия", "series"],
    "name": ["название", "name", "товар", "product", "наименование"],
    "sku": ["артикул", "sku", "код", "code", "1c", "инвойс", "invoice"],
    "product_type": ["тип", "type", "прямой", "угловой", "прямой/угловой"],
    "diameter": ["диаметр", "diameter", "диам", "ø", "d", "диаметр тела", "body diameter"],
    "length": ["длина", "length", "l", "высота десны", "gum height"],
    "height": ["высота абатмента", "abutment height", "высота", "height", "абатмент"],
    "unit": ["ед", "unit", "единица", "измерения", "изм"],
    "quantity": ["количество", "quantity", "кол-во", "остаток", "склад", "qty"],
    "show_immediately": ["показывать", "видимость", "visibility", "show"],
}

# --- Структура по категориям ---
# Для каждой категории: какие уровни навигации и как маппятся колонки Excel
# Excel "Категория" → первый уровень (подкатегория в каталоге)
# Excel "Линейка" → второй уровень (линейка в каталоге)
CATEGORY_STRUCTURE = {
    "Импланты": {
        "has_subcategory": False,  # Нет колонки "Категория", только Линейка
        "excel_line_to": "line",    # Линейка → line (AnyRidge, AnyOne)
        "navigation": ["line", "diameter", "length"],  # Линейка → Диаметр → Длина
        "has_type": False,
        "has_height": False,
    },
    "Протетика": {
        "has_subcategory": True,    # Колонка "Категория" = EzPost, ZrGen, MU
        "excel_category_to": "subcategory",
        "excel_line_to": "line",    # Линейка = AnyRidge, AnyOne
        "navigation": ["subcategory", "line", "type", "diameter", "length", "height"],
        "has_type": True,
        "has_height": True,
    },
    "Лаборатория": {
        "has_subcategory": True,
        "excel_category_to": "subcategory",
        "excel_line_to": "line",
        "navigation": ["subcategory", "line", "type", "diameter", "length", "height"],
        "has_type": True,   # Может быть пустым — тогда показываем 0°
        "has_height": True,
    },
    "Наборы": {
        "has_subcategory": True,
        "excel_category_to": "subcategory",
        "excel_line_to": "line",
        "navigation": ["subcategory", "line", "product"],  # Товар без размеров
        "has_type": False,
        "has_height": False,
    },
    "материалы": {
        "has_subcategory": True,
        "excel_category_to": "subcategory",
        "excel_line_to": "line",
        "navigation": ["subcategory", "line", "product"],
        "has_type": False,
        "has_height": False,
    },
}

# --- Тип (угол) vs Диаметр ---
# Значения типа: только эти числа считаются углами (градусы)
TYPE_ANGLES = (0, 17, 25, 30, 15, 20)

# Диапазон диаметров: числа в этом диапазоне НЕ показываются как типы
DIAMETER_RANGE = (2.0, 10.0)

# --- Маппинг листов Excel на категории ---
SHEET_TO_CATEGORY = {
    "импланты": "Импланты",
    "implants": "Импланты",
    "имплант": "Импланты",
    "протетика": "Протетика",
    "prosthetics": "Протетика",
    "протез": "Протетика",
    "лаборатория": "Лаборатория",
    "laboratory": "Лаборатория",
    "lab": "Лаборатория",
    "лаборатор": "Лаборатория",
    "наборы": "Наборы",
    "kits": "Наборы",
    "набор": "Наборы",
    "материалы": "материалы",
    "materials": "материалы",
    "материал": "материалы",
}

# Листы, которые не обрабатываются
SKIP_SHEETS = ["инструкция", "instruction", "readme"]

# --- Видимость категорий при входе в каталог ---
# Главные категории (в Продукции): показываются сразу. Остальные — в «Дополнительно».
# При нажатии «Дополнительно» показываются ТОЛЬКО категории, не входящие в главные.
MAIN_CATEGORIES = ["Импланты", "Протетика"]

# --- Отображение диаметра имплантов ---
# [] только для размера тела (Ø5.5 [4.8]). Простой диаметр — без скобок (Ø3.5)


# Кеш каталога в памяти (заполняется из БД при старте)
_catalog_cache: dict = {}
_visibility_cache: dict = {}


def get_catalog() -> dict:
    """
    Централизованный доступ к каталогу.
    Приоритет: 1) кеш из БД  2) catalog_data.py  3) пустой dict.
    """
    if _catalog_cache:
        return _catalog_cache
    try:
        from catalog_data import CATALOG
        return CATALOG
    except ImportError:
        return {}


def get_visibility() -> dict:
    """Возвращает VISIBILITY dict (из кеша БД или catalog_data.py)."""
    if _visibility_cache:
        return _visibility_cache
    try:
        from catalog_data import VISIBILITY
        return VISIBILITY
    except ImportError:
        return {}


def set_catalog_cache(catalog: dict, visibility: dict) -> None:
    """Установить кеш каталога (вызывается при загрузке из БД)."""
    global _catalog_cache, _visibility_cache
    _catalog_cache = catalog
    _visibility_cache = visibility


async def build_catalog_from_db(session) -> tuple[dict, dict]:
    """
    Строит CATALOG и VISIBILITY из таблицы catalog_items.
    Формат совместим с текущими keyboards и handlers.

    Вызывать при старте бота после загрузки Excel → DB.
    """
    from sqlalchemy import select
    from database.models import CatalogItem

    result = await session.execute(
        select(CatalogItem).where(CatalogItem.is_active.is_(True))
    )
    items = result.scalars().all()

    catalog: dict = {}
    visibility: dict = {}

    for item in items:
        cat = item.category
        if cat not in catalog:
            catalog[cat] = {}
        if cat not in visibility:
            visibility[cat] = {"subcategory": {}, "line": {}, "product": {}}

        product_data = {
            "name": item.product_name,
            "sku": item.sku,
            "unit": item.unit,
            "qty": item.qty,
            "show_immediately": item.show_immediately,
        }
        if item.diameter_body is not None:
            product_data["diameter_body"] = item.diameter_body

        # --- Импланты: line → diameter_key → length → product_data ---
        if cat == "Импланты":
            line = item.line
            if line not in catalog[cat]:
                catalog[cat][line] = {}
            # Обновляем видимость
            vis = visibility[cat]["line"]
            vis[line] = vis.get(line, False) or item.show_immediately

            if item.diameter is not None and item.length is not None:
                diam_key = (item.diameter, item.diameter_body) if item.diameter_body else item.diameter
                if diam_key not in catalog[cat][line]:
                    catalog[cat][line][diam_key] = {}
                catalog[cat][line][diam_key][item.length] = product_data
            else:
                # no_size
                if "no_size" not in catalog[cat][line]:
                    catalog[cat][line]["no_size"] = []
                catalog[cat][line]["no_size"].append(product_data)

        # --- Протетика / Лаборатория: subcategory → line → product_name → type → diam → length → height ---
        elif cat in ("Протетика", "Лаборатория"):
            subcat = item.subcategory or "Основное"
            line = item.line

            if subcat not in catalog[cat]:
                catalog[cat][subcat] = {}
            if line not in catalog[cat][subcat]:
                catalog[cat][subcat][line] = {}

            vis_sub = visibility[cat]["subcategory"]
            vis_sub[subcat] = vis_sub.get(subcat, False) or item.show_immediately
            vis_line = visibility[cat]["line"]
            vis_line[line] = vis_line.get(line, False) or item.show_immediately

            if item.diameter is not None and item.length is not None:
                pname = item.product_name
                vis_prod = visibility[cat]["product"]
                vis_prod[pname] = vis_prod.get(pname, False) or item.show_immediately

                if pname not in catalog[cat][subcat][line]:
                    catalog[cat][subcat][line][pname] = {}
                pnode = catalog[cat][subcat][line][pname]

                # product_type → diameter → length → [height →] product_data
                ptype = int(float(item.product_type)) if item.product_type and item.product_type.replace(".", "").replace("-", "").isdigit() else item.product_type
                if ptype is not None:
                    if ptype not in pnode:
                        pnode[ptype] = {}
                    dnode = pnode[ptype]
                else:
                    dnode = pnode

                diam = item.diameter
                if diam not in dnode:
                    dnode[diam] = {}
                lnode = dnode[diam]

                if item.height is not None:
                    if item.length not in lnode:
                        lnode[item.length] = {}
                    lnode[item.length][item.height] = product_data
                else:
                    lnode[item.length] = product_data
            else:
                # no_size
                if "no_size" not in catalog[cat][subcat][line]:
                    catalog[cat][subcat][line]["no_size"] = []
                catalog[cat][subcat][line]["no_size"].append(product_data)

        # --- Наборы / материалы: subcategory → line → no_size ---
        elif cat in ("Наборы", "материалы"):
            subcat = item.subcategory or "Основное"
            line = item.line

            if subcat not in catalog[cat]:
                catalog[cat][subcat] = {}
            if line not in catalog[cat][subcat]:
                catalog[cat][subcat][line] = {}

            vis_sub = visibility[cat]["subcategory"]
            vis_sub[subcat] = vis_sub.get(subcat, False) or item.show_immediately
            vis_line = visibility[cat]["line"]
            vis_line[line] = vis_line.get(line, False) or item.show_immediately

            if "no_size" not in catalog[cat][subcat][line]:
                catalog[cat][subcat][line]["no_size"] = []
            catalog[cat][subcat][line]["no_size"].append(product_data)

        # --- Прочие категории ---
        else:
            pname = item.product_name
            line = item.line
            if pname not in catalog[cat]:
                catalog[cat][pname] = {}
            if line not in catalog[cat][pname]:
                catalog[cat][pname][line] = {}
            if item.diameter is not None and item.length is not None:
                if item.diameter not in catalog[cat][pname][line]:
                    catalog[cat][pname][line][item.diameter] = {}
                catalog[cat][pname][line][item.diameter][item.length] = product_data
            else:
                if "no_size" not in catalog[cat][pname][line]:
                    catalog[cat][pname][line]["no_size"] = []
                catalog[cat][pname][line]["no_size"].append(product_data)

    set_catalog_cache(catalog, visibility)
    return catalog, visibility
