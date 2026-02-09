# Руководство по настройке расположения кнопок в меню менеджера

## Текущая структура

Сейчас меню менеджера находится в функции `get_manager_menu_kb()` в файле `keyboards/manager_kbs.py`.

## Как работает расположение кнопок

В Telegram Inline клавиатурах каждая строка в массиве `rows` - это одна горизонтальная строка кнопок.

### Пример 1: Кнопки в одну строку (горизонтально)

```python
def get_manager_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню менеджера - кнопки в одну строку"""
    rows = [
        [
            InlineKeyboardButton(text="🛍 Каталог", callback_data="manager:catalog"),
            InlineKeyboardButton(text="📋 Мои заказы", callback_data="manager:orders")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
```

**Результат:**
```
[🛍 Каталог] [📋 Мои заказы]
```

### Пример 2: Кнопки в отдельные строки (вертикально) - текущий вариант

```python
def get_manager_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню менеджера - каждая кнопка в отдельной строке"""
    rows = [
        [InlineKeyboardButton(text="🛍 Каталог продукции", callback_data="manager:catalog")],
        [InlineKeyboardButton(text="📋 Мои заказы", callback_data="manager:orders")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
```

**Результат:**
```
[🛍 Каталог продукции]
[📋 Мои заказы]
```

### Пример 3: Комбинированное расположение

```python
def get_manager_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню менеджера - комбинированное"""
    rows = [
        [
            InlineKeyboardButton(text="🛍 Каталог", callback_data="manager:catalog"),
            InlineKeyboardButton(text="📋 Заказы", callback_data="manager:orders")
        ],
        [
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="manager:settings")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
```

**Результат:**
```
[🛍 Каталог] [📋 Заказы]
[⚙️ Настройки]
```

### Пример 4: Много кнопок в строке (до 3-4 кнопок)

```python
def get_manager_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню менеджера - 3 кнопки в строке"""
    rows = [
        [
            InlineKeyboardButton(text="🛍 Каталог", callback_data="manager:catalog"),
            InlineKeyboardButton(text="📋 Заказы", callback_data="manager:orders"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="manager:stats")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
```

**Результат:**
```
[🛍 Каталог] [📋 Заказы] [📊 Статистика]
```

⚠️ **Важно:** Не рекомендуется размещать более 3-4 кнопок в одной строке, так как они станут слишком маленькими.

### Пример 5: Группировка с разделителями

```python
def get_manager_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню менеджера с группировкой"""
    rows = [
        # Основные функции
        [
            InlineKeyboardButton(text="🛍 Каталог продукции", callback_data="manager:catalog"),
            InlineKeyboardButton(text="📋 Мои заказы", callback_data="manager:orders")
        ],
        # Дополнительные функции (если нужно)
        # [
        #     InlineKeyboardButton(text="📊 Статистика", callback_data="manager:stats"),
        #     InlineKeyboardButton(text="⚙️ Настройки", callback_data="manager:settings")
        # ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
```

## Настройка количества кнопок в строке для каталога

### Категории (make_categories_kb)

**Текущий вариант:** Каждая категория в отдельной строке
```python
for cat in categories:
    rows.append([InlineKeyboardButton(...)])  # Каждая в отдельной строке
```

**Вариант с 2 кнопками в строке:**
```python
rows = []
for i in range(0, len(categories), 2):  # Шаг 2
    row = []
    row.append(InlineKeyboardButton(text=categories[i], ...))
    if i + 1 < len(categories):
        row.append(InlineKeyboardButton(text=categories[i + 1], ...))
    rows.append(row)
```

**Вариант с 3 кнопками в строке:**
```python
rows = []
for i in range(0, len(categories), 3):  # Шаг 3
    row = []
    for j in range(3):
        if i + j < len(categories):
            row.append(InlineKeyboardButton(text=categories[i + j], ...))
    rows.append(row)
```

## Рекомендации

1. **Главное меню:** 1-2 кнопки в строке (удобнее для больших кнопок)
2. **Категории:** 1-2 кнопки в строке (названия могут быть длинными)
3. **Списки товаров:** 1 кнопка в строке (для читаемости)
4. **Действия (Назад, Корзина):** 2 кнопки в строке (компактно)

## Как изменить текущее меню

Откройте файл `keyboards/manager_kbs.py` и найдите функцию `get_manager_menu_kb()` (строка ~582).

### Вариант A: Кнопки в одну строку
```python
def get_manager_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню менеджера"""
    rows = [
        [
            InlineKeyboardButton(text="🛍 Каталог продукции", callback_data="manager:catalog"),
            InlineKeyboardButton(text="📋 Мои заказы", callback_data="manager:orders")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
```

### Вариант B: Оставить как есть (каждая кнопка в отдельной строке)
```python
def get_manager_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню менеджера"""
    rows = [
        [InlineKeyboardButton(text="🛍 Каталог продукции", callback_data="manager:catalog")],
        [InlineKeyboardButton(text="📋 Мои заказы", callback_data="manager:orders")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
```

## Настройка каталога

Для изменения расположения кнопок в каталоге нужно редактировать соответствующие функции:
- `make_categories_kb()` - категории
- `make_lines_kb()` - линейки
- `make_diameters_kb()` - диаметры
- `make_items_kb()` - товары

Принцип тот же: каждая строка в массиве `rows` = одна горизонтальная строка кнопок.

