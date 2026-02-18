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


def get_catalog() -> dict:
    """
    Централизованный доступ к каталогу.
    catalog_data.py перегенерируется из Excel, поэтому import может упасть
    при первом запуске. Возвращает пустой dict если модуль не найден.
    """
    try:
        from catalog_data import CATALOG
        return CATALOG
    except ImportError:
        return {}
