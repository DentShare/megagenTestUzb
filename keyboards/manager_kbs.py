from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import Optional, Dict
from config import config

try:
    from catalog_config import TYPE_ANGLES, DIAMETER_RANGE, MAIN_CATEGORIES
except ImportError:
    TYPE_ANGLES = (0, 17, 25, 30, 15, 20)
    DIAMETER_RANGE = (2.0, 10.0)
    MAIN_CATEGORIES = ["Импланты", "Протетика"]

try:
    from catalog_data import CATALOG, VISIBILITY
except ImportError:
    # Fallback если catalog_data.py не найден
    CATALOG = {
        "Импланты": {
            "AnyRidge": {3.5: [8.5, 10.0, 11.5], 4.0: [8.5, 10.0, 11.5]},
            "AnyOne": {3.5: [8.5, 10.0, 11.5], 4.0: [8.5, 10.0, 11.5]},
        },
        "Наборы": {"Surgical Kit": {"no_size": True}},
    }
    VISIBILITY = {}

# --- Helper Functions ---

def _sort_mixed_values(values):
    """
    Сортирует значения: числа, tuple (d, body), строки.
    """
    def sort_key(v):
        if isinstance(v, (int, float)):
            return (0, float(v), 0)
        if isinstance(v, tuple) and len(v) == 2:
            return (0, float(v[0]), float(v[1]) if v[1] is not None else 0)
        return (1, 0, str(v))
    return sorted(values, key=sort_key)

# --- Callback Data ---
class MenuCallback(CallbackData, prefix="menu"):
    level: int
    category: Optional[str] = None
    category_index: Optional[int] = None  # Индекс категории (для сжатия callback >64 байт)
    subcategory: Optional[str] = None  # Подкатегория для протетики/лаборатории (колонка "Категория" в Excel)
    subcategory_index: Optional[int] = None  # Индекс подкатегории в списке (для длинных названий)
    line: Optional[str] = None  # Для протетики/лаборатории - линейка импланта, для остальных - линейка товара
    line_index: Optional[int] = None  # Индекс линейки (для сжатия callback >64 байт)
    product: Optional[str] = None  # Для протетики/лаборатории - название товара (EZ Post Abutment и т.д.)
    product_index: Optional[int] = None  # Индекс продукта в списке (для длинных названий)
    product_type: Optional[float] = None  # Для протетики: градусы (0, 17, 25, 30)
    product_type_str: Optional[str] = None  # Для протетики: "0 [N]", "17 [N]" — углы с предписанием N (без шестигранника)
    diameter: Optional[float] = None
    diameter_body: Optional[float] = None  # Для имплантов: диаметр тела из [], отличает "4.5 [3.8]" от "4.5"
    length: Optional[float] = None  # Для имплантов - длина, для протетики - высота десны
    height: Optional[float] = None  # Для протетики - высота абатмента
    product_name: Optional[str] = None  # Для товаров без размеров
    action: Optional[str] = None # 'add_to_cart', 'back', 'cart', 'toggle_urgent', 'toggle_delivery', 'submit', 'increase_qty', 'decrease_qty', 'remove_item', 'subcategory', 'show_all_lines', 'show_all_products'
    item_index: Optional[int] = None # Index in cart for quantity changes


def _pack_with_subcategory_fallback(category: str, subcategory: Optional[str], **kwargs) -> str:
    """Packs MenuCallback; progressively uses indices (subcategory_index, category_index, line_index) if >64 bytes."""
    line = kwargs.get("line")

    def _try_pack(**cb_kw) -> str:
        try:
            p = MenuCallback(**cb_kw).pack()
            if len(p.encode("utf-8")) <= 64:
                return p
        except ValueError:
            pass
        return ""

    all_categories = list(CATALOG.keys())
    cat_idx = all_categories.index(category) if category in all_categories else None
    subcat_idx = None
    line_idx = None
    if subcategory and category in CATALOG:
        all_subcategories = list(CATALOG[category].keys())
        subcat_idx = all_subcategories.index(subcategory) if subcategory in all_subcategories else None
        if line and subcat_idx is not None and subcategory in CATALOG[category]:
            line_data = CATALOG[category][subcategory]
            if isinstance(line_data, dict):
                all_lines = list(line_data.keys())
                line_idx = all_lines.index(line) if line in all_lines else None

    base = dict(kwargs)
    base["category"] = category
    base["subcategory"] = subcategory
    if line is not None:
        base["line"] = line

    # 1. Full names
    if p := _try_pack(**base):
        return p
    # 2. subcategory_index
    if subcat_idx is not None:
        base2 = {k: v for k, v in base.items() if k != "subcategory"}
        base2["subcategory_index"] = subcat_idx
        if p := _try_pack(**base2):
            return p
    # 3. category_index + subcategory_index
    if cat_idx is not None and subcat_idx is not None:
        base3 = {k: v for k, v in base2.items() if k != "category"}
        base3["category_index"] = cat_idx
        if p := _try_pack(**base3):
            return p
    # 4. + line_index
    if line_idx is not None:
        base4 = {k: v for k, v in base3.items() if k != "line"}
        base4["line_index"] = line_idx
        if p := _try_pack(**base4):
            return p
    # Fallback: pack as-is (may raise)
    return MenuCallback(**base).pack()


# --- Keyboards ---

def make_categories_kb(show_all: bool = False) -> InlineKeyboardMarkup:
    """
    Клавиатура категорий.
    Главные (Импланты, Протетика) — сразу. Остальные — в «Дополнительно».
    При нажатии «Дополнительно» показываются ТОЛЬКО категории, не входящие в главные.
    
    Args:
        show_all: Если True, показывать только дополнительные категории (Лаборатория, Наборы, материалы).
                  Если False, показывать главные (Импланты, Протетика) и кнопку «Дополнительно».
    """
    # Настройка: количество кнопок в одной строке (1 = вертикально, 2 = по 2 в строке, и т.д.)
    BUTTONS_PER_ROW = getattr(config, "CATEGORY_BUTTONS_PER_ROW", 1)
    
    all_categories = list(CATALOG.keys())
    main_cats = [c for c in MAIN_CATEGORIES if c in all_categories]
    additional_categories = [c for c in all_categories if c not in main_cats]
    
    if show_all:
        # Показываем только дополнительные категории (то, чего нет в главном)
        categories_to_show = additional_categories
    else:
        # Главные категории — сразу, остальные в «Дополнительно»
        categories_to_show = main_cats
    
    rows = []
    
    # Показываем приоритетные категории
    if BUTTONS_PER_ROW == 1:
        # Каждая категория в отдельной строке (вертикально)
        for cat in categories_to_show:
            rows.append([
                InlineKeyboardButton(
                    text=cat,
                    callback_data=MenuCallback(level=1, category=cat).pack()
                )
            ])
    else:
        # Несколько кнопок в строке (горизонтально)
        for i in range(0, len(categories_to_show), BUTTONS_PER_ROW):
            row = []
            for j in range(BUTTONS_PER_ROW):
                if i + j < len(categories_to_show):
                    row.append(InlineKeyboardButton(
                        text=categories_to_show[i + j],
                        callback_data=MenuCallback(level=1, category=categories_to_show[i + j]).pack()
                    ))
            rows.append(row)
    
    # Если есть дополнительные категории и мы на главном экране — кнопка "Дополнительно"
    if additional_categories and not show_all:
        rows.append([
            InlineKeyboardButton(
                text=f"📦 Дополнительно ({len(additional_categories)})",
                callback_data=MenuCallback(level=0, action="show_all_categories").pack()
            )
        ])
    
    # Если показываем дополнительные категории — кнопка "Назад" к главному каталогу
    if show_all and additional_categories:
        rows.append([
            InlineKeyboardButton(
                text="◀ Назад к каталогу",
                callback_data=MenuCallback(level=0, action="back_to_main_categories").pack()
            )
        ])
    
    # Возврат в главное меню и корзина
    rows.append([
        InlineKeyboardButton(text="🏠 В главное меню", callback_data="manager:main"),
        InlineKeyboardButton(text="🛒 Корзина", callback_data=MenuCallback(level=99, action="cart").pack())
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def make_products_kb_for_category(category: str, show_all: bool = False) -> InlineKeyboardMarkup:
    """
    Клавиатура товаров (видов) для протетики/лаборатории/наборов.
    Использует VISIBILITY из Excel для определения, что показывать сразу, а что в "Дополнительно".
    
    Args:
        category: Категория (Протетика, Лаборатория, Наборы)
        show_all: Если True, показывать все товары. Если False, используем VISIBILITY из Excel.
    """
    if category not in CATALOG:
        return make_categories_kb()
    
    # Получаем все товары (виды) из каталога
    all_products = list(CATALOG[category].keys())
    
    # Разделяем на показываемые сразу и дополнительные на основе VISIBILITY
    if show_all:
        # Показываем все товары
        products_to_show = all_products
        additional_products = []
    else:
        # Используем информацию из VISIBILITY
        products_to_show = []
        additional_products = []
        
        for product in all_products:
            # Проверяем видимость товара (по умолчанию показываем сразу)
            show_immediately = True
            if category in VISIBILITY and "product" in VISIBILITY[category]:
                show_immediately = VISIBILITY[category]["product"].get(product, True)
            
            if show_immediately:
                products_to_show.append(product)
            else:
                additional_products.append(product)
    
    rows = []
    
    # Показываем приоритетные товары
    # Используем индекс для длинных названий, чтобы избежать превышения лимита callback_data (64 байта)
    # Индекс должен быть относительно полного списка all_products
    for product in products_to_show:
        # Если название продукта слишком длинное (>30 байт в UTF-8), используем индекс
        product_bytes = product.encode('utf-8')
        if len(product_bytes) > 30:
            # Находим индекс в полном списке all_products
            product_index = all_products.index(product)
            callback_data = MenuCallback(level=2, category=category, product_index=product_index).pack()
        else:
            callback_data = MenuCallback(level=2, category=category, product=product).pack()
        
        rows.append([
            InlineKeyboardButton(
                text=product,
                callback_data=callback_data
            )
        ])
    
    # Если есть дополнительные товары, показываем кнопку "Дополнительно"
    if additional_products and not show_all:
        rows.append([
            InlineKeyboardButton(
                text=f"📦 Дополнительно ({len(additional_products)})",
                callback_data=MenuCallback(level=1, category=category, action="show_all_products").pack()
            )
        ])
    
    # Кнопки навигации
    rows.append([
        InlineKeyboardButton(text="⬅ Назад", callback_data=MenuCallback(level=0).pack()),
        InlineKeyboardButton(text="🏠 В каталог", callback_data=MenuCallback(level=0).pack()),
        InlineKeyboardButton(text="🏠 В главное меню", callback_data="manager:main"),
        InlineKeyboardButton(text="🛒 Корзина", callback_data=MenuCallback(level=99, action="cart").pack())
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def make_lines_kb(category: str, show_all: bool = False) -> InlineKeyboardMarkup:
    """
    Клавиатура линеек.
    Настройка: измените BUTTONS_PER_ROW для изменения количества кнопок в строке.
    
    Args:
        category: Категория товаров
        show_all: Если True, показывать все линейки. Если False, приоритетные отдельно, остальные в "Дополнительно".
    """
    # Настройка: количество кнопок в одной строке
    BUTTONS_PER_ROW = getattr(config, "LINE_BUTTONS_PER_ROW", 1)
    
    # Level 1 - для протетики/лаборатории показываем линейки имплантов, для остальных - линейки товаров
    if category not in CATALOG:
        return make_categories_kb()
    
    # Для протетики, лаборатории и наборов - проверяем наличие подкатегорий
    if category in ["Протетика", "Лаборатория", "Наборы", "материалы"]:
        if category not in CATALOG:
            return make_categories_kb()
        
        # Проверяем наличие подкатегорий.
        #
        # Структура без подкатегорий (частый случай):
        #   CATALOG[category][product][line][...] ...
        # и структура с подкатегориями:
        #   CATALOG[category][subcategory][product][line][...] ...
        #
        # Раньше использовалась эвристика "словарь внутри словаря", но она не отличает product->line от subcategory->product,
        # из-за чего в меню «Выберите линейку импланта» могли показываться названия товаров (как на скрине).
        #
        # Category (колонка "Категория") -> Sub_category (колонка "Линейка"). Первый уровень всегда показываем.
        first_level = list(CATALOG[category].keys())
        has_subcategories = len(first_level) > 0
        
        if has_subcategories:
            # Есть подкатегории - показываем их
            subcategories = sorted(first_level)
            
            # Разделяем на показываемые сразу и дополнительные на основе VISIBILITY
            if show_all:
                subcategories_to_show = subcategories
                additional_subcategories = []
            else:
                subcategories_to_show = []
                additional_subcategories = []
                
                for subcat in subcategories:
                    # Проверяем видимость подкатегории (по умолчанию показываем сразу)
                    show_immediately = True
                    if category in VISIBILITY and "subcategory" in VISIBILITY[category]:
                        show_immediately = VISIBILITY[category]["subcategory"].get(subcat, True)
                    
                    if show_immediately:
                        subcategories_to_show.append(subcat)
                    else:
                        additional_subcategories.append(subcat)
            
            rows = []
            # Создаем полный список всех подкатегорий для индексации
            all_subcategories = sorted(first_level)
            for subcat in subcategories_to_show:
                # Проверяем длину подкатегории и полного callback data
                # Используем более консервативный лимит (20 байт) для подкатегории
                subcat_bytes = subcat.encode('utf-8')
                
                # Пробуем сначала с полным названием
                try:
                    test_callback = MenuCallback(level=1, category=category, subcategory=subcat, action="subcategory").pack()
                    if len(test_callback.encode('utf-8')) <= 64:
                        callback_data = test_callback
                    else:
                        # Если слишком длинный, используем индекс (относительно полного списка)
                        subcat_index = all_subcategories.index(subcat)
                        callback_data = MenuCallback(level=1, category=category, subcategory_index=subcat_index, action="subcategory").pack()
                except ValueError:
                    # Если даже при попытке упаковки возникает ошибка, используем индекс
                    subcat_index = all_subcategories.index(subcat)
                    callback_data = MenuCallback(level=1, category=category, subcategory_index=subcat_index, action="subcategory").pack()
                
                rows.append([
                    InlineKeyboardButton(
                        text=subcat,
                        callback_data=callback_data
                    )
                ])
            
            # Если есть дополнительные подкатегории, показываем кнопку "Дополнительно"
            if additional_subcategories and not show_all:
                rows.append([
                    InlineKeyboardButton(
                        text=f"📦 Дополнительно ({len(additional_subcategories)})",
                        callback_data=MenuCallback(level=1, category=category, action="show_all_subcategories").pack()
                    )
                ])
            
            rows.append([
                InlineKeyboardButton(text="⬅ Назад", callback_data=MenuCallback(level=0).pack()),
                InlineKeyboardButton(text="🏠 В каталог", callback_data=MenuCallback(level=0).pack()),
                InlineKeyboardButton(text="🏠 В главное меню", callback_data="manager:main"),
                InlineKeyboardButton(text="🛒 Корзина", callback_data=MenuCallback(level=99, action="cart").pack())
            ])
            return InlineKeyboardMarkup(inline_keyboard=rows)
        
        # Нет подкатегорий - показываем линейки имплантов
        # Собираем все уникальные линейки имплантов из всех товаров
        all_lines = set()
        for product in CATALOG[category].values():
            if isinstance(product, dict):
                all_lines.update(product.keys())
        all_lines = sorted(list(all_lines))
        
        # Разделяем на показываемые сразу и дополнительные на основе VISIBILITY
        if show_all:
            lines_to_show = all_lines
            additional_lines = []
        else:
            # Используем информацию из VISIBILITY
            lines_to_show = []
            additional_lines = []
            
            for line in all_lines:
                # Проверяем видимость линейки (по умолчанию показываем сразу)
                show_immediately = True
                if category in VISIBILITY and "line" in VISIBILITY[category]:
                    show_immediately = VISIBILITY[category]["line"].get(line, True)
                
                if show_immediately:
                    lines_to_show.append(line)
                else:
                    additional_lines.append(line)
        
        rows = []
        
        # Показываем приоритетные линейки
        if BUTTONS_PER_ROW == 1:
            for line in lines_to_show:
                rows.append([
                    InlineKeyboardButton(
                        text=line,
                        callback_data=MenuCallback(level=2, category=category, line=line).pack()
                    )
                ])
        else:
            for i in range(0, len(lines_to_show), BUTTONS_PER_ROW):
                row = []
                for j in range(BUTTONS_PER_ROW):
                    if i + j < len(lines_to_show):
                        row.append(InlineKeyboardButton(
                            text=lines_to_show[i + j],
                            callback_data=MenuCallback(level=2, category=category, line=lines_to_show[i + j]).pack()
                        ))
                rows.append(row)
        
        # Если есть дополнительные линейки, показываем кнопку "Дополнительно"
        if additional_lines and not show_all:
            rows.append([
                InlineKeyboardButton(
                    text=f"📦 Дополнительно ({len(additional_lines)})",
                    callback_data=MenuCallback(level=1, category=category, action="show_all_lines").pack()
                )
            ])
        
        # Кнопки навигации
        rows.append([
            InlineKeyboardButton(text="⬅ Назад", callback_data=MenuCallback(level=0).pack()),
            InlineKeyboardButton(text="🏠 В каталог", callback_data=MenuCallback(level=0).pack()),
            InlineKeyboardButton(text="🏠 В главное меню", callback_data="manager:main"),
            InlineKeyboardButton(text="🛒 Корзина", callback_data=MenuCallback(level=99, action="cart").pack())
        ])
        return InlineKeyboardMarkup(inline_keyboard=rows)
    elif category == "Импланты":
        # Для имплантов - показываем линейки напрямую
        # Структура: category -> line
        all_lines = list(CATALOG[category].keys())
    else:
        # Для остальных категорий (Наборы, материалы) - стандартные линейки
        all_lines = list(CATALOG[category].keys())
    
    # Разделяем на показываемые сразу и дополнительные на основе VISIBILITY
    if show_all or category != "Импланты":
        # Показываем все линейки
        lines_to_show = all_lines
        additional_lines = []
    else:
        # Используем информацию из VISIBILITY
        lines_to_show = []
        additional_lines = []
        
        for line in all_lines:
            # Проверяем видимость линейки (по умолчанию показываем сразу)
            show_immediately = True
            if category in VISIBILITY and "line" in VISIBILITY[category]:
                show_immediately = VISIBILITY[category]["line"].get(line, True)
            
            if show_immediately:
                lines_to_show.append(line)
            else:
                additional_lines.append(line)
    
    rows = []
    
    # Показываем приоритетные линейки
    if BUTTONS_PER_ROW == 1:
        # Каждая линейка в отдельной строке
        for line in lines_to_show:
            rows.append([
                InlineKeyboardButton(
                    text=line,
                    callback_data=MenuCallback(level=2, category=category, line=line).pack()
                )
            ])
    else:
        # Несколько кнопок в строке
        for i in range(0, len(lines_to_show), BUTTONS_PER_ROW):
            row = []
            for j in range(BUTTONS_PER_ROW):
                if i + j < len(lines_to_show):
                    row.append(InlineKeyboardButton(
                        text=lines_to_show[i + j],
                        callback_data=MenuCallback(level=2, category=category, line=lines_to_show[i + j]).pack()
                    ))
            rows.append(row)
    
    # Если есть дополнительные линейки, показываем кнопку "Дополнительно"
    if additional_lines and not show_all and category == "Импланты":
        rows.append([
            InlineKeyboardButton(
                text=f"📦 Дополнительно ({len(additional_lines)})",
                callback_data=MenuCallback(level=1, category=category, action="show_all_lines").pack()
            )
        ])
    
    # Кнопки навигации
    rows.append([
        InlineKeyboardButton(text="⬅ Назад", callback_data=MenuCallback(level=0).pack()),
        InlineKeyboardButton(text="🏠 В каталог", callback_data=MenuCallback(level=0).pack()),
        InlineKeyboardButton(text="🏠 В главное меню", callback_data="manager:main"),
        InlineKeyboardButton(text="🛒 Корзина", callback_data=MenuCallback(level=99, action="cart").pack())
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def make_diameters_kb(category: str, line: str) -> InlineKeyboardMarkup:
    """
    Клавиатура диаметров.
    Настройка: измените BUTTONS_PER_ROW для изменения количества кнопок в строке.
    """
    # Настройка: количество кнопок в одной строке
    BUTTONS_PER_ROW = getattr(config, "DIAMETER_BUTTONS_PER_ROW", 2)
    
    # Level 2 - для протетики/лаборатории показываем товары для выбранной линейки импланта
    if category not in CATALOG:
        return make_lines_kb(category)
    
    # Для протетики/лаборатории/наборов диаметры показываются после выбора типа (level 4 -> 5)
    # Здесь показываем диаметры только для имплантов
    
    # Для остальных категорий - показываем диаметры
    if line not in CATALOG[category]:
        return make_lines_kb(category)
    
    all_keys = list(CATALOG[category][line].keys())
    
    # Разделяем на диаметры (числа и tuple) и товары без размеров
    diameters = [k for k in all_keys if isinstance(k, (int, float)) or (isinstance(k, tuple) and len(k) == 2)]
    has_no_size = "no_size" in all_keys
    
    # Сортируем диаметры
    sorted_diameters = _sort_mixed_values(diameters)
    rows = []
    
    def _diam_cb(diam):
        if isinstance(diam, tuple) and len(diam) == 2:
            return MenuCallback(level=3, category=category, line=line, diameter=diam[0], diameter_body=diam[1]).pack()
        return MenuCallback(level=3, category=category, line=line, diameter=diam).pack()
    
    def _diam_text(diam):
        # [] только для размера тела. Простой диаметр — без скобок: Ø3.5
        if isinstance(diam, tuple) and len(diam) == 2:
            return f"Ø{diam[0]} [{diam[1]}]"
        return f"Ø{diam}"
    
    if BUTTONS_PER_ROW == 1:
        # Каждый диаметр в отдельной строке
        for diam in sorted_diameters:
            rows.append([
                InlineKeyboardButton(
                    text=_diam_text(diam),
                    callback_data=_diam_cb(diam)
                )
            ])
    else:
        # Несколько кнопок в строке
        for i in range(0, len(sorted_diameters), BUTTONS_PER_ROW):
            row = []
            for j in range(BUTTONS_PER_ROW):
                if i + j < len(sorted_diameters):
                    diam = sorted_diameters[i + j]
                    row.append(InlineKeyboardButton(
                        text=_diam_text(diam),
                        callback_data=_diam_cb(diam)
                    ))
            rows.append(row)
    
    # Если есть товары без размеров, добавляем кнопку
    if has_no_size:
        rows.append([
            InlineKeyboardButton(
                text="📦 Товары без размеров",
                callback_data=MenuCallback(level=5, category=category, line=line, action="no_size_list").pack()
            )
        ])
    
    rows.append([
        InlineKeyboardButton(text="⬅ Назад", callback_data=MenuCallback(level=1, category=category, line=line).pack()),
        InlineKeyboardButton(text="🏠 В каталог", callback_data=MenuCallback(level=0).pack()),
        InlineKeyboardButton(text="🏠 В главное меню", callback_data="manager:main")
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def make_lines_for_subcategory_kb(category: str, subcategory: str, show_all: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура Sub_category (линеек) для выбранной Category (протетика/лаборатория/наборы/материалы)."""
    if category not in CATALOG or subcategory not in CATALOG[category]:
        return make_lines_kb(category)
    # Структура: Category -> Sub_category (excel_line) -> product -> ...
    subcategory_data = CATALOG[category][subcategory]
    if isinstance(subcategory_data, dict):
        all_lines = sorted(k for k in subcategory_data.keys() if k != "no_size")
    else:
        all_lines = []
    
    if not all_lines:
        return make_lines_kb(category)
    
    # Разделяем на показываемые сразу и дополнительные на основе VISIBILITY
    if show_all:
        lines_to_show = all_lines
        additional_lines = []
    else:
        # Используем информацию из VISIBILITY
        lines_to_show = []
        additional_lines = []
        
        for line in all_lines:
            # Проверяем видимость линейки (по умолчанию показываем сразу)
            show_immediately = True
            if category in VISIBILITY and "line" in VISIBILITY[category]:
                show_immediately = VISIBILITY[category]["line"].get(line, True)
            
            if show_immediately:
                lines_to_show.append(line)
            else:
                additional_lines.append(line)
    
    BUTTONS_PER_ROW = getattr(config, "LINE_BUTTONS_PER_ROW", 1)
    rows = []
    all_subcategories = list(CATALOG[category].keys())
    subcategory_index = all_subcategories.index(subcategory) if subcategory in all_subcategories else None
    
    def _line_cb(line_name: str) -> str:
        """
        Строит callback для линии с учетом ограничения 64 байта.
        Сначала пробуем subcategory по имени, если слишком длинно — используем subcategory_index.
        """
        # Пытаемся упаковать с полным названием подкатегории
        try:
            cb = MenuCallback(level=2, category=category, subcategory=subcategory, line=line_name).pack()
            if len(cb.encode("utf-8")) <= 64:
                return cb
        except ValueError:
            pass
        # Если длина >64 или ошибка упаковки — используем индекс
        if subcategory_index is not None:
            return MenuCallback(
                level=2, category=category, subcategory_index=subcategory_index, line=line_name
            ).pack()
        # Fallback: всё равно пробуем с именем (лучше ошибка, чем тишина)
        return MenuCallback(level=2, category=category, subcategory=subcategory, line=line_name).pack()
    
    # Показываем приоритетные линейки
    if BUTTONS_PER_ROW == 1:
        for line in lines_to_show:
            rows.append([
                InlineKeyboardButton(
                    text=line,
                    callback_data=_line_cb(line)
                )
            ])
    else:
        for i in range(0, len(lines_to_show), BUTTONS_PER_ROW):
            row = []
            for j in range(BUTTONS_PER_ROW):
                if i + j < len(lines_to_show):
                    line_name = lines_to_show[i + j]
                    row.append(InlineKeyboardButton(
                        text=line_name,
                        callback_data=_line_cb(line_name)
                    ))
            rows.append(row)
    
    # Если есть дополнительные линейки, показываем кнопку "Дополнительно"
    if additional_lines and not show_all:
        all_subcategories = list(CATALOG[category].keys())
        subcategory_index = all_subcategories.index(subcategory) if subcategory in all_subcategories else None
        callback_data = None
        try:
            cb_full = MenuCallback(level=1, category=category, subcategory=subcategory, action="show_all_lines").pack()
            if len(cb_full.encode('utf-8')) <= 64:
                callback_data = cb_full
        except ValueError:
            pass
        if callback_data is None and subcategory_index is not None:
            callback_data = MenuCallback(level=1, category=category, subcategory_index=subcategory_index, action="show_all_lines").pack()
        if callback_data is None:
            callback_data = MenuCallback(level=1, category=category, subcategory=subcategory, action="show_all_lines").pack()
        
        rows.append([
            InlineKeyboardButton(
                text=f"📦 Дополнительно ({len(additional_lines)})",
                callback_data=callback_data
            )
        ])
    
    rows.append([
        InlineKeyboardButton(text="⬅ Назад", callback_data=MenuCallback(level=0, category=category).pack()),
        InlineKeyboardButton(text="🏠 В каталог", callback_data=MenuCallback(level=0).pack()),
        InlineKeyboardButton(text="🏠 В главное меню", callback_data="manager:main")
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def make_products_for_line_kb(category: str, line: str, show_all: bool = False, subcategory: str = None) -> InlineKeyboardMarkup:
    """Клавиатура товаров (типов) для выбранной Category и Sub_category (протетика/лаборатория/наборы/материалы)."""
    if category not in CATALOG:
        return make_lines_kb(category)
    # Структура: Category (subcategory) -> Sub_category (line) -> product -> type -> diameter -> ... или no_size
    products_with_line = []
    no_size_names = set()  # названия товаров из no_size (для кнопки "В корзину" сразу)
    if subcategory and subcategory in CATALOG[category]:
        line_data = CATALOG[category][subcategory].get(line) if isinstance(CATALOG[category][subcategory], dict) else None
        if isinstance(line_data, dict):
            products_with_line = [k for k in line_data.keys() if k != "no_size"]
            if "no_size" in line_data and isinstance(line_data["no_size"], list):
                for item in line_data["no_size"]:
                    if isinstance(item, dict) and item.get("name"):
                        no_size_names.add(item["name"])
                for n in no_size_names:
                    if n not in products_with_line:
                        products_with_line.append(n)
    if not products_with_line:
        return make_lines_kb(category)
    
    # Разделяем на показываемые сразу и дополнительные на основе VISIBILITY
    if show_all:
        products_to_show = products_with_line
        additional_products = []
    else:
        # Используем информацию из VISIBILITY
        products_to_show = []
        additional_products = []
        
        for product in products_with_line:
            # Проверяем видимость товара (по умолчанию показываем сразу)
            show_immediately = True
            if category in VISIBILITY and "product" in VISIBILITY[category]:
                show_immediately = VISIBILITY[category]["product"].get(product, True)
            
            if show_immediately:
                products_to_show.append(product)
            else:
                additional_products.append(product)
    
    rows = []
    all_subcategories = list(CATALOG[category].keys())
    
    def _cb_no_size(prod_name: str) -> str:
        """Callback для товара без размеров. При длине >64 байт используем product_index и subcategory_index."""
        product_index = all_products.index(prod_name) if prod_name in all_products else None
        # Сначала пробуем product_name (если короткое)
        try:
            if subcategory:
                packed = MenuCallback(level=3, category=category, subcategory=subcategory, line=line, product_name=prod_name, action="add_to_cart").pack()
            else:
                packed = MenuCallback(level=3, category=category, line=line, product_name=prod_name, action="add_to_cart").pack()
            if len(packed.encode('utf-8')) <= 64:
                return packed
        except (ValueError, Exception):
            pass
        # Иначе product_index
        if product_index is None:
            raise ValueError("product_index required for long product_name")
        if subcategory:
            subcat_idx = all_subcategories.index(subcategory) if subcategory in all_subcategories else None
            # Пробуем с subcategory по имени; если >64 байт — используем subcategory_index
            try:
                packed = MenuCallback(level=3, category=category, subcategory=subcategory, line=line, product_index=product_index, action="add_to_cart").pack()
                if len(packed.encode('utf-8')) <= 64:
                    return packed
            except (ValueError, Exception):
                pass
            if subcat_idx is not None:
                return MenuCallback(level=3, category=category, subcategory_index=subcat_idx, line=line, product_index=product_index, action="add_to_cart").pack()
            return MenuCallback(level=3, category=category, subcategory=subcategory, line=line, product_index=product_index, action="add_to_cart").pack()
        return MenuCallback(level=3, category=category, line=line, product_index=product_index, action="add_to_cart").pack()
    
    all_products = products_with_line
    for product in products_to_show:
        # Товары без размеров (no_size): кнопка сразу ведёт в запрос количества
        if product in no_size_names:
            rows.append([
                InlineKeyboardButton(text=product, callback_data=_cb_no_size(product))
            ])
            continue
        # Если название продукта слишком длинное, используем индекс
        product_bytes = product.encode('utf-8')
        if len(product_bytes) > 30:
            product_index = all_products.index(product) if product in all_products else None
            if product_index is not None:
                # Если подкатегория длинная, используем индекс
                if subcategory:
                    subcat_bytes = subcategory.encode('utf-8')
                    if len(subcat_bytes) > 30:
                        all_subcategories = list(CATALOG[category].keys())
                        subcategory_index = all_subcategories.index(subcategory) if subcategory in all_subcategories else None
                        if subcategory_index is not None:
                            callback_data = MenuCallback(level=3, category=category, subcategory_index=subcategory_index, line=line, product_index=product_index).pack()
                        else:
                            callback_data = MenuCallback(level=3, category=category, subcategory=subcategory, line=line, product_index=product_index).pack()
                    else:
                        callback_data = MenuCallback(level=3, category=category, subcategory=subcategory, line=line, product_index=product_index).pack()
                else:
                    callback_data = MenuCallback(level=3, category=category, line=line, product_index=product_index).pack()
            else:
                # Если подкатегория длинная, используем индекс
                if subcategory:
                    subcat_bytes = subcategory.encode('utf-8')
                    if len(subcat_bytes) > 30:
                        all_subcategories = list(CATALOG[category].keys())
                        subcategory_index = all_subcategories.index(subcategory) if subcategory in all_subcategories else None
                        if subcategory_index is not None:
                            callback_data = MenuCallback(level=3, category=category, subcategory_index=subcategory_index, line=line, product=product).pack()
                        else:
                            callback_data = MenuCallback(level=3, category=category, subcategory=subcategory, line=line, product=product).pack()
                    else:
                        callback_data = MenuCallback(level=3, category=category, subcategory=subcategory, line=line, product=product).pack()
                else:
                    callback_data = MenuCallback(level=3, category=category, line=line, product=product).pack()
        else:
            # Если подкатегория длинная, используем индекс
            if subcategory:
                subcat_bytes = subcategory.encode('utf-8')
                if len(subcat_bytes) > 30:
                    all_subcategories = list(CATALOG[category].keys())
                    subcategory_index = all_subcategories.index(subcategory) if subcategory in all_subcategories else None
                    if subcategory_index is not None:
                        callback_data = MenuCallback(level=3, category=category, subcategory_index=subcategory_index, line=line, product=product).pack()
                    else:
                        callback_data = MenuCallback(level=3, category=category, subcategory=subcategory, line=line, product=product).pack()
                else:
                    callback_data = MenuCallback(level=3, category=category, subcategory=subcategory, line=line, product=product).pack()
            else:
                callback_data = MenuCallback(level=3, category=category, line=line, product=product).pack()
        
        rows.append([
            InlineKeyboardButton(
                text=product,
                callback_data=callback_data
            )
        ])
    
    # Если есть дополнительные товары, показываем кнопку "Дополнительно"
    if additional_products and not show_all:
        # Если подкатегория длинная, используем индекс
        if subcategory:
            subcat_bytes = subcategory.encode('utf-8')
            if len(subcat_bytes) > 30:
                all_subcategories = list(CATALOG[category].keys())
                subcategory_index = all_subcategories.index(subcategory) if subcategory in all_subcategories else None
                if subcategory_index is not None:
                    callback_data = MenuCallback(level=2, category=category, subcategory_index=subcategory_index, line=line, action="show_all_products").pack()
                else:
                    callback_data = MenuCallback(level=2, category=category, subcategory=subcategory, line=line, action="show_all_products").pack()
            else:
                callback_data = MenuCallback(level=2, category=category, subcategory=subcategory, line=line, action="show_all_products").pack()
        else:
            callback_data = MenuCallback(level=2, category=category, line=line, action="show_all_products").pack()
        
        rows.append([
            InlineKeyboardButton(
                text=f"📦 Дополнительно ({len(additional_products)})",
                callback_data=callback_data
            )
        ])
    
    # Назад: при subcategory — к списку линеек этой подкатегории, иначе к подкатегориям
    if subcategory:
        try:
            subcat_bytes = subcategory.encode('utf-8')
            if len(subcat_bytes) > 30:
                idx = all_subcategories.index(subcategory) if subcategory in all_subcategories else None
                back_cb = MenuCallback(level=1, category=category, subcategory_index=idx, action="subcategory").pack() if idx is not None else MenuCallback(level=1, category=category, subcategory=subcategory, action="subcategory").pack()
            else:
                back_cb = MenuCallback(level=1, category=category, subcategory=subcategory, action="subcategory").pack()
        except (ValueError, Exception):
            back_cb = MenuCallback(level=1, category=category, subcategory=subcategory, action="subcategory").pack()
    else:
        back_cb = MenuCallback(level=1, category=category).pack()
    rows.append([
        InlineKeyboardButton(text="⬅ Назад", callback_data=back_cb),
        InlineKeyboardButton(text="🏠 В каталог", callback_data=MenuCallback(level=0).pack()),
        InlineKeyboardButton(text="🏠 В главное меню", callback_data="manager:main")
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def make_lines_for_product_kb(category: str, product: str) -> InlineKeyboardMarkup:
    """Клавиатура линеек имплантов для выбранного товара (протетика/лаборатория/наборы)"""
    if category not in CATALOG or product not in CATALOG[category]:
        return make_lines_kb(category)
    
    # Получаем все линейки имплантов для выбранного товара
    # Структура: category -> product -> line (линейка импланта)
    product_data = CATALOG[category][product]
    if isinstance(product_data, dict):
        lines = sorted(list(product_data.keys()))
    else:
        lines = []
    
    # Находим индекс продукта для использования в callback_data, если название длинное
    all_products = list(CATALOG[category].keys())
    product_index = all_products.index(product) if product in all_products else None
    
    rows = []
    for line in lines:
        # Если название продукта слишком длинное, используем индекс
        product_bytes = product.encode('utf-8')
        if len(product_bytes) > 30 and product_index is not None:
            callback_data = MenuCallback(level=3, category=category, line=line, product_index=product_index).pack()
        else:
            callback_data = MenuCallback(level=3, category=category, line=line, product=product).pack()
        
        rows.append([
            InlineKeyboardButton(
                text=line,
                callback_data=callback_data
            )
        ])
    
    rows.append([
        InlineKeyboardButton(text="⬅ Назад", callback_data=MenuCallback(level=1, category=category).pack()),
        InlineKeyboardButton(text="🏠 В каталог", callback_data=MenuCallback(level=0).pack()),
        InlineKeyboardButton(text="🏠 В главное меню", callback_data="manager:main")
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def _is_diameter_key(key) -> bool:
    """Проверяет, похож ли ключ на диаметр. Поддерживает float и tuple (d, body)."""
    if isinstance(key, tuple) and len(key) == 2:
        try:
            return _is_diameter_key(key[0])
        except Exception:
            return False
    try:
        k = float(key)
        return DIAMETER_RANGE[0] <= k <= DIAMETER_RANGE[1]
    except (ValueError, TypeError):
        return False

def _parse_type_key(key):
    """Преобразует ключ в тип. Возвращает (float, None) для углов или (None, str) для [N]. None если диаметр/длина.
    Использует TYPE_ANGLES и DIAMETER_RANGE из catalog_config."""
    # Сначала исключаем диаметры (2–10) — они никогда не являются углами
    if _is_diameter_key(key):
        return (None, None)
    # Варианты [N] (без шестигранника)
    if isinstance(key, str) and "[n]" in key.lower():
        return (None, key)
    if isinstance(key, str) and key in ["прямой", "угловой"]:
        return (0.0 if key == "прямой" else 17.0, None)
    # Числовые ключи — только известные углы (из catalog_config)
    try:
        k = float(key)
        if k in TYPE_ANGLES or (isinstance(k, float) and k == int(k) and int(k) in TYPE_ANGLES):
            return (float(k), None)
    except (ValueError, TypeError):
        pass
    return (None, None)

def _format_type_display(pt_float, pt_str) -> str:
    """Форматирует тип для отображения: 0° → «0°», «0 [N]» → «0° [N]»."""
    if pt_str:
        num = pt_str.replace("[N]", "").replace("[n]", "").strip()
        if num.isdigit():
            return f"{num}° [N]"
        return "[N]"
    if pt_float is not None:
        return f"{int(pt_float)}°" if isinstance(pt_float, float) and pt_float == int(pt_float) else f"{pt_float}°"
    return ""

def make_prosthetics_types_for_line_kb(category: str, subcategory: str, line: str) -> InlineKeyboardMarkup:
    """Клавиатура типов (углов) по линейке. Типы: 0°, 17°, 30° и варианты [N] (без шестигранника)."""
    rows = []
    types_numeric = set()
    types_str = set()
    has_diameter_only = False
    if subcategory and category in CATALOG and subcategory in CATALOG[category] and line in CATALOG[category][subcategory]:
        line_data = CATALOG[category][subcategory][line]
        if isinstance(line_data, dict):
            for product_key, product_data in line_data.items():
                if product_key == "no_size" or not isinstance(product_data, dict):
                    continue
                for key in product_data.keys():
                    pt_float, pt_str = _parse_type_key(key)
                    if pt_float is not None:
                        types_numeric.add(pt_float)
                    elif pt_str:
                        types_str.add(pt_str)
                    elif _is_diameter_key(key):
                        has_diameter_only = True
    if not types_numeric and not types_str and has_diameter_only:
        types_numeric = {0.0}
    if not types_numeric and not types_str:
        return make_products_for_line_kb(category, line, subcategory=subcategory)
    for pt in sorted(types_numeric):
        type_text = _format_type_display(pt, None)
        rows.append([
            InlineKeyboardButton(
                text=type_text,
                callback_data=MenuCallback(level=3, category=category, subcategory=subcategory, line=line, product_type=float(pt)).pack()
            )
        ])
    for pt_str in sorted(types_str):
        type_text = _format_type_display(None, pt_str)
        rows.append([
            InlineKeyboardButton(
                text=type_text,
                callback_data=MenuCallback(level=3, category=category, subcategory=subcategory, line=line, product_type_str=pt_str).pack()
            )
        ])
    back_cb = MenuCallback(level=1, category=category, subcategory=subcategory, action="subcategory").pack()
    try:
        if len(subcategory.encode("utf-8")) > 30:
            all_sub = list(CATALOG[category].keys())
            idx = all_sub.index(subcategory) if subcategory in all_sub else None
            if idx is not None:
                back_cb = MenuCallback(level=1, category=category, subcategory_index=idx, action="subcategory").pack()
    except Exception:
        pass
    rows.append([
        InlineKeyboardButton(text="⬅ Назад", callback_data=back_cb),
        InlineKeyboardButton(text="🏠 В каталог", callback_data=MenuCallback(level=0).pack()),
        InlineKeyboardButton(text="🏠 В главное меню", callback_data="manager:main")
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def make_product_type_kb(category: str, line: str, product: str, subcategory: str = None) -> InlineKeyboardMarkup:
    """Клавиатура типов товара для протетики (при выборе по товару). Путь: Category -> Sub_category -> product."""
    if subcategory and category in CATALOG and subcategory in CATALOG[category] and line in CATALOG[category][subcategory]:
        line_data = CATALOG[category][subcategory][line]
        product_data = line_data.get(product) if isinstance(line_data, dict) else None
    else:
        product_data = None
    if not product_data:
        return make_products_for_line_kb(category, line, subcategory=subcategory)
    types_numeric = []
    types_str = []
    if isinstance(product_data, dict):
        for key in product_data.keys():
            pt_float, pt_str = _parse_type_key(key)
            if pt_float is not None:
                types_numeric.append(pt_float)
            elif pt_str:
                types_str.append(pt_str)
    
    rows = []
    for pt in sorted(types_numeric):
        type_text = _format_type_display(pt, None)
        rows.append([
            InlineKeyboardButton(
                text=type_text,
                callback_data=MenuCallback(level=4, category=category, subcategory=subcategory or None, line=line, product=product, product_type=float(pt)).pack()
            )
        ])
    for pt_str in sorted(types_str):
        type_text = _format_type_display(None, pt_str)
        rows.append([
            InlineKeyboardButton(
                text=type_text,
                callback_data=MenuCallback(level=4, category=category, subcategory=subcategory or None, line=line, product=product, product_type_str=pt_str).pack()
            )
        ])
    if not rows:
        return make_prosthetics_diameters_kb(category, line, product, product_type=None, subcategory=subcategory)
    
    back_cb = MenuCallback(level=2, category=category, subcategory=subcategory or None, line=line).pack()
    rows.append([
        InlineKeyboardButton(text="⬅ Назад", callback_data=back_cb),
        InlineKeyboardButton(text="🏠 В каталог", callback_data=MenuCallback(level=0).pack()),
        InlineKeyboardButton(text="🏠 В главное меню", callback_data="manager:main")
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def _collect_diameters_from_line(line_data: dict, product_type) -> list:
    """Собирает все диаметры по всем товарам линейки для данного типа (угол или [N])."""
    diameters_set = set()
    if not isinstance(line_data, dict):
        return []
    for product_key, product_line_data in line_data.items():
        if product_key == "no_size" or not isinstance(product_line_data, dict):
            continue
        pd = product_line_data
        if product_type is not None:
            type_level = _catalog_get(pd, product_type)
            if type_level is not None:
                for k in type_level.keys():
                    try:
                        diameters_set.add(float(k))
                    except (ValueError, TypeError):
                        pass
            else:
                for k in pd.keys():
                    if _is_diameter_key(k):
                        try:
                            diameters_set.add(float(k))
                        except (ValueError, TypeError):
                            pass
        else:
            for k in pd.keys():
                if _is_diameter_key(k) or isinstance(k, (int, float)):
                    try:
                        diameters_set.add(float(k))
                    except (ValueError, TypeError):
                        pass
    return sorted(diameters_set)

def _catalog_get(d: dict, key) -> Optional[dict]:
    """Получить значение из каталога по ключу. Каталог может хранить ключи как int, float или str."""
    if d is None or not isinstance(d, dict) or key is None:
        return None
    v = d.get(key)
    if v is not None:
        return v
    if isinstance(key, (int, float)) and key == int(key):
        v = d.get(int(key)) or d.get(str(int(key)))
        if v is not None:
            return v
    return d.get(str(key))


def _get_nested(pd: dict, *keys) -> Optional[dict]:
    """Получает вложенный dict по ключам, пробует int/float/str варианты."""
    cur = pd
    for k in keys:
        cur = _catalog_get(cur, k)
        if cur is None:
            return None
    return cur if isinstance(cur, dict) else None

def _collect_lengths_from_line(line_data: dict, product_type, diameter) -> list:
    """Собирает все длины (высота десны) по всем товарам линейки для тип+диаметр."""
    lengths_set = set()
    if not isinstance(line_data, dict):
        return []
    for product_key, product_line_data in line_data.items():
        if product_key == "no_size" or not isinstance(product_line_data, dict):
            continue
        pd = product_line_data
        # Структура с типом: pd[type][diameter] или без типа: pd[diameter]
        level2 = _get_nested(pd, product_type, diameter) if product_type is not None else _get_nested(pd, diameter)
        if level2 is None and product_type is not None:
            level2 = _get_nested(pd, diameter)
        if isinstance(level2, dict):
            for k in level2.keys():
                try:
                    lengths_set.add(float(k))
                except (ValueError, TypeError):
                    pass
    return sorted(lengths_set)


def _lengths_with_has_abutment(line_data: dict, product_type, diameter) -> list:
    """
    Возвращает список (length, has_abutment_height) для линейки.
    has_abutment_height=False если у позиции нет параметра «высота абатмента» (товар сразу по длине).
    """
    result = {}  # length -> has_abutment
    if not isinstance(line_data, dict):
        return []
    for product_key, product_line_data in line_data.items():
        if product_key == "no_size" or not isinstance(product_line_data, dict):
            continue
        pd = product_line_data
        level2 = _get_nested(pd, product_type, diameter) if product_type is not None else _get_nested(pd, diameter)
        if level2 is None and product_type is not None:
            level2 = _get_nested(pd, diameter)
        if not isinstance(level2, dict):
            continue
        for k, ld in level2.items():
            try:
                length_f = float(k)
            except (ValueError, TypeError):
                continue
            if not isinstance(ld, dict):
                continue
            # Если под длиной лежит продукт (есть sku) — нет уровня «высота абатмента»
            if ld.get("sku") is not None:
                result[length_f] = False
            else:
                # Есть вложенные ключи (высоты абатмента)
                result[length_f] = True
    return sorted(result.items())

def _collect_heights_from_line(line_data: dict, product_type, diameter, length) -> list:
    """Собирает все высоты абатмента по всем товарам линейки для тип+диаметр+длина."""
    heights_set = set()
    if not isinstance(line_data, dict):
        return []
    for product_key, product_line_data in line_data.items():
        if product_key == "no_size" or not isinstance(product_line_data, dict):
            continue
        pd = product_line_data
        level3 = _get_nested(pd, product_type, diameter, length) if product_type is not None else _get_nested(pd, diameter, length)
        if level3 is None and product_type is not None:
            level3 = _get_nested(pd, diameter, length)
        if isinstance(level3, dict):
            for k in level3.keys():
                try:
                    if isinstance(k, (int, float)) or (isinstance(k, str) and k.replace(".", "").replace("-", "").isdigit()):
                        heights_set.add(float(k))
                except (ValueError, TypeError):
                    pass
    return sorted(heights_set)

def make_prosthetics_diameters_for_line_kb(category: str, subcategory: str, line: str, product_type: Optional[float] = None, product_type_str: Optional[str] = None) -> InlineKeyboardMarkup:
    """Клавиатура диаметров по линейке (тип уже выбран: угол или [N])."""
    BUTTONS_PER_ROW = getattr(config, "DIAMETER_BUTTONS_PER_ROW", 2)
    pt_key = product_type_str if product_type_str else product_type
    diameters = []
    if subcategory and category in CATALOG and subcategory in CATALOG[category] and line in CATALOG[category][subcategory]:
        line_data = CATALOG[category][subcategory][line]
        diameters = _collect_diameters_from_line(line_data, pt_key)
    if not diameters:
        return make_prosthetics_types_for_line_kb(category, subcategory, line)
    rows = []
    def _diam_cb(diam):
        kw = dict(level=4, line=line, diameter=diam)
        if product_type_str:
            kw["product_type_str"] = product_type_str
        else:
            kw["product_type"] = product_type
        return _pack_with_subcategory_fallback(category, subcategory, **kw)
    if BUTTONS_PER_ROW == 1:
        for diam in sorted(diameters):
            rows.append([InlineKeyboardButton(text=f"Ø{diam}", callback_data=_diam_cb(diam))])
    else:
        sorted_d = sorted(diameters)
        for i in range(0, len(sorted_d), BUTTONS_PER_ROW):
            row = [InlineKeyboardButton(text=f"Ø{sorted_d[i + j]}", callback_data=_diam_cb(sorted_d[i + j])) for j in range(BUTTONS_PER_ROW) if i + j < len(sorted_d)]
            rows.append(row)
    back_cb = _pack_with_subcategory_fallback(category, subcategory, level=2, line=line)
    rows.append([
        InlineKeyboardButton(text="⬅ Назад", callback_data=back_cb),
        InlineKeyboardButton(text="🏠 В каталог", callback_data=MenuCallback(level=0).pack()),
        InlineKeyboardButton(text="🏠 В главное меню", callback_data="manager:main")
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def make_prosthetics_diameters_kb(category: str, line: str, product: str, product_type: Optional[str] = None, subcategory: str = None) -> InlineKeyboardMarkup:
    """Клавиатура диаметров для протетики (при выборе по товару). Путь: Category -> Sub_category -> product."""
    BUTTONS_PER_ROW = getattr(config, "DIAMETER_BUTTONS_PER_ROW", 2)
    if subcategory and category in CATALOG and subcategory in CATALOG[category] and line in CATALOG[category][subcategory]:
        line_data = CATALOG[category][subcategory][line]
        product_line_data = line_data.get(product) if isinstance(line_data, dict) else None
    else:
        product_line_data = None
    if not product_line_data:
        return make_product_type_kb(category, line, product, subcategory=subcategory)
    diameters = []
    
    type_level = _catalog_get(product_line_data, product_type) if product_type is not None else None
    if type_level is not None:
        diameters = list(type_level.keys())
    elif product_type is None:
        if isinstance(product_line_data, dict):
            test_key = list(product_line_data.keys())[0] if product_line_data else None
            if isinstance(test_key, (int, float)):
                diameters = list(product_line_data.keys())
    
    rows = []
    def _diam_cb(diam):
        return MenuCallback(level=5, category=category, subcategory=subcategory or None, line=line, product=product, product_type=product_type, diameter=diam).pack()
    if BUTTONS_PER_ROW == 1:
        for diam in sorted(diameters):
            rows.append([InlineKeyboardButton(text=f"Ø{diam}", callback_data=_diam_cb(diam))])
    else:
        for i in range(0, len(diameters), BUTTONS_PER_ROW):
            row = [InlineKeyboardButton(text=f"Ø{sorted(diameters)[i + j]}", callback_data=_diam_cb(sorted(diameters)[i + j])) for j in range(BUTTONS_PER_ROW) if i + j < len(diameters)]
            rows.append(row)
    back_cb = MenuCallback(level=3, category=category, subcategory=subcategory or None, line=line, product=product).pack()
    rows.append([
        InlineKeyboardButton(text="⬅ Назад", callback_data=back_cb),
        InlineKeyboardButton(text="🏠 В каталог", callback_data=MenuCallback(level=0).pack()),
        InlineKeyboardButton(text="🏠 В главное меню", callback_data="manager:main")
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def make_prosthetics_gum_height_kb(category: str, line: str, product: str, product_type: Optional[str], diameter: float, stock_data: Dict[float, int], subcategory: str = None) -> InlineKeyboardMarkup:
    """Клавиатура высоты десны для протетики. Если у позиции нет высоты абатмента — кнопка ведёт сразу в корзину (height=None)."""
    BUTTONS_PER_ROW = getattr(config, "GUM_HEIGHT_BUTTONS_PER_ROW", 2)
    if subcategory and category in CATALOG and subcategory in CATALOG[category] and line in CATALOG[category][subcategory]:
        line_data = CATALOG[category][subcategory][line]
        product_line_data = line_data.get(product) if isinstance(line_data, dict) else None
    else:
        product_line_data = None
    if not product_line_data:
        return make_prosthetics_diameters_kb(category, line, product, product_type, subcategory=subcategory)
    # Один товар — передаём как «линейку» из одного продукта»
    line_data_single = {product: product_line_data}
    length_has_abutment = _lengths_with_has_abutment(line_data_single, product_type, diameter)
    if not length_has_abutment:
        return make_prosthetics_diameters_kb(category, line, product, product_type, subcategory=subcategory)
    rows = []
    def _cb(length, has_abutment):
        if has_abutment:
            return MenuCallback(
                level=5, category=category, subcategory=subcategory or None, line=line, product=product,
                product_type=product_type, diameter=diameter, length=length,
                action="select_abutment_height"
            ).pack()
        return MenuCallback(
            level=5, category=category, subcategory=subcategory or None, line=line, product=product,
            product_type=product_type, diameter=diameter, length=length, height=None,
            action="add_to_cart"
        ).pack()
    if BUTTONS_PER_ROW == 1:
        for length, has_abutment in length_has_abutment:
            qty = stock_data.get(length, 0)
            text = f"📏 {length} мм ({qty} шт)" if qty > 0 else f"📏 {length} мм (0 шт) ❌"
            rows.append([InlineKeyboardButton(text=text, callback_data=_cb(length, has_abutment))])
    else:
        for i in range(0, len(length_has_abutment), BUTTONS_PER_ROW):
            row = []
            for j in range(BUTTONS_PER_ROW):
                if i + j < len(length_has_abutment):
                    length, has_abutment = length_has_abutment[i + j]
                    qty = stock_data.get(length, 0)
                    text = f"📏 {length} мм" if qty > 0 else f"📏 {length} мм ❌"
                    row.append(InlineKeyboardButton(text=text, callback_data=_cb(length, has_abutment)))
            rows.append(row)
    
    back_cb = MenuCallback(level=4, category=category, subcategory=subcategory or None, line=line, product=product, product_type=product_type).pack()
    rows.append([
        InlineKeyboardButton(text="⬅ Назад", callback_data=back_cb),
        InlineKeyboardButton(text="🏠 В каталог", callback_data=MenuCallback(level=0).pack()),
        InlineKeyboardButton(text="🏠 В главное меню", callback_data="manager:main")
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def make_prosthetics_gum_height_for_line_kb(category: str, subcategory: str, line: str, product_type, diameter: float, stock_data: Dict[float, int], product_type_str: Optional[str] = None) -> InlineKeyboardMarkup:
    """Клавиатура длины (высота десны) по линейке. Если у позиции нет высоты абатмента — кнопка ведёт сразу в корзину (height=None)."""
    BUTTONS_PER_ROW = getattr(config, "GUM_HEIGHT_BUTTONS_PER_ROW", 2)
    pt_key = product_type_str if product_type_str else product_type
    length_has_abutment = []
    if subcategory and category in CATALOG and subcategory in CATALOG[category] and line in CATALOG[category][subcategory]:
        line_data = CATALOG[category][subcategory][line]
        length_has_abutment = _lengths_with_has_abutment(line_data, pt_key, diameter)
    if not length_has_abutment:
        return make_prosthetics_diameters_for_line_kb(category, subcategory, line, product_type, product_type_str)
    rows = []
    def _cb_abutment(length):
        kw = dict(level=5, line=line, diameter=diameter, length=length, action="select_abutment_height")
        if product_type_str:
            kw["product_type_str"] = product_type_str
        else:
            kw["product_type"] = product_type
        return _pack_with_subcategory_fallback(category, subcategory, **kw)
    def _cb_add_no_height(length):
        kw = dict(level=5, line=line, diameter=diameter, length=length, height=None, action="add_to_cart")
        if product_type_str:
            kw["product_type_str"] = product_type_str
        else:
            kw["product_type"] = product_type
        return _pack_with_subcategory_fallback(category, subcategory, **kw)
    for length, has_abutment in length_has_abutment:
        qty = stock_data.get(length, 0)
        text = f"📏 {length} мм ({qty} шт)" if qty > 0 else f"📏 {length} мм (0 шт) ❌"
        cb = _cb_abutment(length) if has_abutment else _cb_add_no_height(length)
        rows.append([InlineKeyboardButton(text=text, callback_data=cb)])
    back_kw = dict(level=3, line=line)
    if product_type_str:
        back_kw["product_type_str"] = product_type_str
    else:
        back_kw["product_type"] = product_type
    back_cb = _pack_with_subcategory_fallback(category, subcategory, **back_kw)
    rows.append([
        InlineKeyboardButton(text="⬅ Назад", callback_data=back_cb),
        InlineKeyboardButton(text="🏠 В каталог", callback_data=MenuCallback(level=0).pack()),
        InlineKeyboardButton(text="🏠 В главное меню", callback_data="manager:main")
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def make_prosthetics_abutment_height_for_line_kb(category: str, subcategory: str, line: str, product_type, diameter: float, gum_height: float, stock_data: Dict[float, int], product_type_str: Optional[str] = None) -> InlineKeyboardMarkup:
    """Клавиатура высоты абатмента по линейке. product_type_str — для вариантов [N]."""
    BUTTONS_PER_ROW = getattr(config, "ABUTMENT_HEIGHT_BUTTONS_PER_ROW", 2)
    rows = []
    heights = sorted(stock_data.keys())
    def _cb(height):
        kw = dict(level=5, line=line, diameter=diameter, length=gum_height, height=height, action="add_to_cart")
        if product_type_str:
            kw["product_type_str"] = product_type_str
        else:
            kw["product_type"] = product_type
        return _pack_with_subcategory_fallback(category, subcategory, **kw)
    if BUTTONS_PER_ROW == 1:
        for height in heights:
            qty = stock_data.get(height, 0)
            text = f"📏 {height} мм ({qty} шт)" if qty > 0 else f"📏 {height} мм (0 шт) ❌"
            rows.append([
                InlineKeyboardButton(text=text, callback_data=_cb(height))
            ])
    else:
        for i in range(0, len(heights), BUTTONS_PER_ROW):
            row = []
            for j in range(BUTTONS_PER_ROW):
                if i + j < len(heights):
                    height = heights[i + j]
                    qty = stock_data.get(height, 0)
                    text = f"📏 {height} мм ({qty} шт)" if qty > 0 else f"📏 {height} мм (0 шт) ❌"
                    row.append(InlineKeyboardButton(text=text, callback_data=_cb(height)))
            rows.append(row)
    back_kw = dict(level=4, line=line, diameter=diameter)
    if product_type_str:
        back_kw["product_type_str"] = product_type_str
    else:
        back_kw["product_type"] = product_type
    back_cb = _pack_with_subcategory_fallback(category, subcategory, **back_kw)
    rows.append([
        InlineKeyboardButton(text="⬅ Назад", callback_data=back_cb),
        InlineKeyboardButton(text="🏠 В каталог", callback_data=MenuCallback(level=0).pack()),
        InlineKeyboardButton(text="🏠 В главное меню", callback_data="manager:main")
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def make_prosthetics_abutment_height_kb(category: str, line: str, product: str, product_type: Optional[str], diameter: float, gum_height: float, stock_data: Dict[float, int], subcategory: str = None) -> InlineKeyboardMarkup:
    """Клавиатура высоты абатмента для протетики."""
    BUTTONS_PER_ROW = getattr(config, "ABUTMENT_HEIGHT_BUTTONS_PER_ROW", 2)
    
    rows = []
    heights = sorted(stock_data.keys())
    
    if BUTTONS_PER_ROW == 1:
        for height in heights:
            qty = stock_data.get(height, 0)
            text = f"📏 {height} мм ({qty} шт)" if qty > 0 else f"📏 {height} мм (0 шт) ❌"
            rows.append([
                InlineKeyboardButton(
                    text=text,
                    callback_data=MenuCallback(
                        level=5, category=category, subcategory=subcategory or None, line=line, product=product,
                        product_type=product_type, diameter=diameter, length=gum_height,
                        height=height, action="add_to_cart"
                    ).pack()
                )
            ])
    else:
        for i in range(0, len(heights), BUTTONS_PER_ROW):
            row = []
            for j in range(BUTTONS_PER_ROW):
                if i + j < len(heights):
                    height = heights[i + j]
                    qty = stock_data.get(height, 0)
                    text = f"📏 {height} мм ({qty} шт)" if qty > 0 else f"📏 {height} мм (0 шт) ❌"
                    row.append(InlineKeyboardButton(
                        text=text,
                        callback_data=MenuCallback(
                            level=5, category=category, subcategory=subcategory or None, line=line, product=product,
                            product_type=product_type, diameter=diameter, length=gum_height,
                            height=height, action="add_to_cart"
                        ).pack()
                    ))
            rows.append(row)
    
    back_cb = MenuCallback(level=5, category=category, subcategory=subcategory or None, line=line, product=product, product_type=product_type, diameter=diameter).pack()
    rows.append([
        InlineKeyboardButton(text="⬅ Назад", callback_data=back_cb),
        InlineKeyboardButton(text="🏠 В каталог", callback_data=MenuCallback(level=0).pack()),
        InlineKeyboardButton(text="🏠 В главное меню", callback_data="manager:main")
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def make_items_kb(category: str, line: str, diameter: float, stock_data: Dict[float, int], product_type: Optional[str] = None, diameter_body: Optional[float] = None) -> InlineKeyboardMarkup:
    """
    Клавиатура товаров с размерами (импланты).
    diameter_body: для имплантов "4.5 [3.8]" — диаметр тела, отличает от "4.5".
    """
    # Настройка: количество кнопок в одной строке
    BUTTONS_PER_ROW = getattr(config, "ITEM_BUTTONS_PER_ROW", 1)
    
    # Level 3 (Items) - товары с размерами
    # Для протетики: показываем высоту десны, затем будет выбор высоты абатмента
    # Для имплантов: показываем длину
    
    if category == "Протетика" and product_type is not None:
        # Для протетики - показываем высоту десны
        return make_prosthetics_gum_height_kb(category, line, product_type, diameter, stock_data)
    
    # Для имплантов - ключ диаметра: (diameter, diameter_body) если diameter_body, иначе diameter
    diam_key = (diameter, diameter_body) if diameter_body is not None else diameter
    
    # Получаем данные товаров из каталога
    catalog_items = {}
    if category in CATALOG and line in CATALOG[category]:
        if product_type is not None and product_type in CATALOG[category][line]:
            if diam_key in CATALOG[category][line][product_type]:
                catalog_items = CATALOG[category][line][product_type][diam_key]
        elif diam_key in CATALOG[category][line]:
            catalog_items = CATALOG[category][line][diam_key]
    
    def _pack_add_to_cart(length_val: float) -> str:
        """Pack add_to_cart callback; fallback to indices if >64 bytes."""
        def _try(**kw) -> str:
            try:
                p = MenuCallback(**kw).pack()
                if len(p.encode("utf-8")) <= 64:
                    return p
            except ValueError:
                pass
            return ""
        base = dict(level=4, category=category, line=line, diameter=diameter, length=length_val, action="add_to_cart")
        if diameter_body is not None:
            base["diameter_body"] = diameter_body
        if p := _try(**base):
            return p
        # Fallback: category_index + line_index
        all_cats = list(CATALOG.keys())
        cat_idx = all_cats.index(category) if category in all_cats else None
        all_lines = list(CATALOG.get(category, {}).keys()) if category in CATALOG else []
        line_idx = all_lines.index(line) if line in all_lines else None
        if cat_idx is not None and line_idx is not None:
            base2 = {k: v for k, v in base.items() if k not in ("category", "line")}
            base2["category_index"] = cat_idx
            base2["line_index"] = line_idx
            if p := _try(**base2):
                return p
        return MenuCallback(**base).pack()
    
    diam_display = f"Ø{diameter} [{diameter_body}]" if diameter_body is not None else f"Ø{diameter}"
    rows = []
    
    if BUTTONS_PER_ROW == 1:
        for length, qty in sorted(stock_data.items()):
            product_info = catalog_items.get(length, {})
            product_name = product_info.get("name", f"{line} {diam_display} L{length}")
            unit = product_info.get("unit", "шт")
            text = f"📏 {length} мм ({qty} {unit})" if qty > 0 else f"📏 {length} мм (0 {unit}) ❌"
            cb = _pack_add_to_cart(length)
            rows.append([InlineKeyboardButton(text=text, callback_data=cb)])
    else:
        sorted_lengths = sorted(stock_data.items())
        for i in range(0, len(sorted_lengths), BUTTONS_PER_ROW):
            row = []
            for j in range(BUTTONS_PER_ROW):
                if i + j < len(sorted_lengths):
                    length, qty = sorted_lengths[i + j]
                    product_info = catalog_items.get(length, {})
                    unit = product_info.get("unit", "шт")
                    text = f"📏 {length} мм" if qty > 0 else f"📏 {length} мм ❌"
                    cb = _pack_add_to_cart(length)
                    row.append(InlineKeyboardButton(text=text, callback_data=cb))
            rows.append(row)
    
    rows.append([
        InlineKeyboardButton(text="⬅ Назад", callback_data=MenuCallback(level=2, category=category, line=line).pack()),
        InlineKeyboardButton(text="🏠 В каталог", callback_data=MenuCallback(level=0).pack()),
        InlineKeyboardButton(text="🏠 В главное меню", callback_data="manager:main")
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def make_no_size_items_kb(category: str, line: str, stock_data: Dict[str, int]) -> InlineKeyboardMarkup:
    """
    Клавиатура товаров без размеров.
    Настройка: измените BUTTONS_PER_ROW для изменения количества кнопок в строке.
    """
    # Настройка: количество кнопок в одной строке
    BUTTONS_PER_ROW = getattr(config, "NO_SIZE_BUTTONS_PER_ROW", 1)
    
    if category not in CATALOG or line not in CATALOG[category] or "no_size" not in CATALOG[category][line]:
        return make_lines_kb(category)
    
    no_size_items = CATALOG[category][line]["no_size"]
    rows = []
    
    if isinstance(no_size_items, list):
        if BUTTONS_PER_ROW == 1:
            for item in no_size_items:
                if isinstance(item, dict):
                    name = item.get("name", "Товар")
                    qty = stock_data.get(item.get("sku", name), 0)
                    text = f"{name} ({qty} шт)" if qty > 0 else f"{name} (0 шт) ❌"
                else:
                    name = str(item)
                    qty = stock_data.get(name, 0)
                    text = f"{name} ({qty} шт)" if qty > 0 else f"{name} (0 шт) ❌"
                
                rows.append([
                    InlineKeyboardButton(
                        text=text,
                        callback_data=MenuCallback(
                            level=5, category=category, line=line,
                            product_name=name, action="no_size_list"
                        ).pack()
                    )
                ])
        else:
            for i in range(0, len(no_size_items), BUTTONS_PER_ROW):
                row = []
                for j in range(BUTTONS_PER_ROW):
                    if i + j < len(no_size_items):
                        item = no_size_items[i + j]
                        if isinstance(item, dict):
                            name = item.get("name", "Товар")
                            qty = stock_data.get(item.get("sku", name), 0)
                            text = f"{name}" if qty > 0 else f"{name} ❌"
                        else:
                            name = str(item)
                            qty = stock_data.get(name, 0)
                            text = f"{name}" if qty > 0 else f"{name} ❌"
                        
                        row.append(InlineKeyboardButton(
                            text=text,
                            callback_data=MenuCallback(
                                level=5, category=category, line=line,
                                product_name=name, action="no_size_list"
                            ).pack()
                        ))
                rows.append(row)
    
    rows.append([
        InlineKeyboardButton(text="⬅ Назад", callback_data=MenuCallback(level=2, category=category, line=line).pack()),
        InlineKeyboardButton(text="🏠 В каталог", callback_data=MenuCallback(level=0).pack()),
        InlineKeyboardButton(text="🏠 В главное меню", callback_data="manager:main")
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def make_cart_kb(is_urgent: bool, delivery_type: str, cart: list = None) -> InlineKeyboardMarkup:
    """
    Клавиатура корзины.
    Настройка: измените расположение кнопок в массиве rows.
    """
    rows = []
    
    # Кнопки управления корзиной
    rows.append([
        InlineKeyboardButton(
            text="🗑 Очистить корзину",
            callback_data=MenuCallback(level=99, action="clear_cart").pack()
        )
    ])
    
    # Кнопки срочности и доставки в одну строку
    urgent_text = "🔥 Срочный" if not is_urgent else "✅ Срочный"
    delivery_text = "🚚 Курьер" if delivery_type == "courier" else "🚕 Такси"
    
    rows.append([
        InlineKeyboardButton(
            text=urgent_text,
            callback_data=MenuCallback(level=99, action="toggle_urgent").pack()
        ),
        InlineKeyboardButton(
            text=delivery_text,
            callback_data=MenuCallback(level=99, action="toggle_delivery").pack()
        )
    ])
    
    # Кнопки управления товарами в корзине
    if cart:
        for idx, item in enumerate(cart):
            item_name_short = item['name'][:30] + "..." if len(item['name']) > 30 else item['name']
            rows.append([
                InlineKeyboardButton(
                    text=f"➕ {item_name_short}",
                    callback_data=MenuCallback(level=99, action="increase_qty", item_index=idx).pack()
                ),
                InlineKeyboardButton(
                    text=f"➖ {item['quantity']} шт",
                    callback_data=MenuCallback(level=99, action="decrease_qty", item_index=idx).pack()
                ),
                InlineKeyboardButton(
                    text="🗑",
                    callback_data=MenuCallback(level=99, action="remove_item", item_index=idx).pack()
                )
            ])
    
    # Кнопка оформления заказа
    rows.append([
        InlineKeyboardButton(
            text="✅ Оформить заказ",
            callback_data=MenuCallback(level=99, action="submit_order").pack()
        )
    ])
    
    # Кнопки возврата
    rows.append([
        InlineKeyboardButton(text="⬅ Вернуться в каталог", callback_data=MenuCallback(level=0).pack()),
        InlineKeyboardButton(text="🏠 В главное меню", callback_data="manager:main")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=rows)

def make_quantity_kb(max_quantity: int = 20) -> InlineKeyboardMarkup:
    """
    Клавиатура для выбора количества товара.
    Создает кнопки от 1 до max_quantity (по умолчанию 20).
    Кнопки расположены по 5 в строке для удобства.
    """
    rows = []
    buttons_per_row = 5
    
    # Создаем кнопки от 1 до max_quantity
    for i in range(1, max_quantity + 1, buttons_per_row):
        row = []
        for j in range(buttons_per_row):
            if i + j <= max_quantity:
                row.append(
                    InlineKeyboardButton(
                        text=str(i + j),
                        callback_data=MenuCallback(level=98, action="select_quantity", item_index=i + j).pack()
                    )
                )
        rows.append(row)
    
    # Кнопка "Отмена" в отдельной строке
    rows.append([
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=MenuCallback(level=99, action="cancel_quantity").pack()
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=rows)

# --- Manager Orders List ---

def _order_status_icon(status) -> str:
    """Цветные кружки статуса: жёлтый=сборка, синий=доставка, зелёный=доставлен, красный=отменён."""
    from database.models import OrderStatus
    if status == OrderStatus.CANCELED:
        return "🔴"
    if status == OrderStatus.DELIVERED:
        return "🟢"
    if status == OrderStatus.DELIVERING:
        return "🔵"
    # NEW, ASSEMBLY, READY_FOR_PICKUP — собирается на складе
    return "🟡"


def make_manager_orders_list_kb(
    orders: list,
    page: int = 0,
    per_page: int = 15,
    total_count: int = 0,
) -> InlineKeyboardMarkup:
    """
    Клавиатура заказов менеджера в виде кнопок.
    Каждая кнопка: [кружок статуса] #номер ФИО врача.
    С пагинацией.
    """
    rows = []
    for order in orders:
        icon = _order_status_icon(order.status)
        doctor_name = (order.clinic.doctor_name or "—") if order.clinic else "—"
        # Ограничение текста кнопки ~60 символов (лимит Telegram)
        btn_text = f"{icon} #{order.id} {doctor_name}"[:60]
        rows.append([
            InlineKeyboardButton(
                text=btn_text,
                callback_data=f"manager:order:{order.id}"
            )
        ])
    # Пагинация
    total_pages = max(1, (total_count + per_page - 1) // per_page) if total_count else 1
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="◀ Назад", callback_data=f"manager:orders:page:{page - 1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="Вперёд ▶", callback_data=f"manager:orders:page:{page + 1}"))
    if nav_row:
        rows.append(nav_row)
    rows.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="manager:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_manager_menu_kb() -> InlineKeyboardMarkup:
    """
    Главное меню менеджера.
    
    НАСТРОЙКА РАСПОЛОЖЕНИЯ КНОПОК:
    
    Вариант 1: Кнопки в одну строку (горизонтально)
    rows = [
        [
            InlineKeyboardButton(text="🛍 Каталог", callback_data="manager:catalog"),
            InlineKeyboardButton(text="📋 Мои заказы", callback_data="manager:orders")
        ]
    ]
    
    Вариант 2: Кнопки в отдельные строки (вертикально) - ТЕКУЩИЙ
    rows = [
        [InlineKeyboardButton(text="🛍 Каталог", callback_data="manager:catalog")],
        [InlineKeyboardButton(text="📋 Мои заказы", callback_data="manager:orders")],
    ]
    
    Вариант 3: Комбинированное
    rows = [
        [
            InlineKeyboardButton(text="🛍 Каталог", callback_data="manager:catalog"),
            InlineKeyboardButton(text="📋 Заказы", callback_data="manager:orders")
        ],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="manager:settings")]
    ]
    """
    # ТЕКУЩАЯ КОНФИГУРАЦИЯ: каждая кнопка в отдельной строке
    rows = [
        [InlineKeyboardButton(text="🛍 Каталог продукции", callback_data="manager:catalog")],
        [InlineKeyboardButton(text="📂 Карта продукции", callback_data="manager:product_map")],
        [InlineKeyboardButton(text="📋 Мои заказы", callback_data="manager:orders")],
        [InlineKeyboardButton(text="🔄 Замены товаров", callback_data="manager:replacements")],
    ]
    
    # РАСКОММЕНТИРУЙТЕ НИЖЕ для кнопок в одну строку:
    # rows = [
    #     [
    #         InlineKeyboardButton(text="🛍 Каталог продукции", callback_data="manager:catalog"),
    #         InlineKeyboardButton(text="📋 Мои заказы", callback_data="manager:orders")
    #     ]
    # ]
    
    return InlineKeyboardMarkup(inline_keyboard=rows)
