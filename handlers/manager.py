import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, UserRole, Order, OrderItem, OrderStatus, DeliveryType, Clinic

logger = logging.getLogger("manager_catalog")
from config import config
from services.one_c import get_stock, get_sku
from services.db_ops import get_user_by_telegram_id
from services.search_service import search_clinics
from keyboards.manager_kbs import (
    MenuCallback, make_categories_kb, make_lines_kb, 
    make_diameters_kb, make_items_kb, make_cart_kb, make_no_size_items_kb,
    make_product_type_kb, make_prosthetics_diameters_kb, 
    make_prosthetics_gum_height_kb, make_prosthetics_abutment_height_kb,
    get_manager_menu_kb, make_quantity_kb, make_manager_orders_list_kb,
)
from states.manager_states import ManagerOrderState
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select

router = Router()


def _get_product_type_key(callback_data: MenuCallback):
    """Возвращает ключ типа для каталога: product_type (float) или product_type_str (str для [N])."""
    if callback_data.product_type_str:
        return callback_data.product_type_str
    return callback_data.product_type


def _fmt_impl_diameter(diameter, diameter_body=None) -> str:
    """Форматирует диаметр импланта. [] только для размера тела: Ø3.5 или Ø5.5 [4.8]."""
    if diameter_body is not None:
        return f"Ø{diameter} [{diameter_body}]"
    return f"Ø{diameter}"


def _catalog_get(d: dict, key):
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


def _get_category_from_callback(callback_data: MenuCallback) -> str:
    """Восстанавливает категорию из callback_data (из индекса, если нужно)."""
    if callback_data.category:
        return callback_data.category
    if callback_data.category_index is not None:
        try:
            from catalog_data import CATALOG
            all_categories = list(CATALOG.keys())
            if 0 <= callback_data.category_index < len(all_categories):
                return all_categories[callback_data.category_index]
        except ImportError:
            pass
    return None


def _get_subcategory_from_callback(callback_data: MenuCallback) -> str:
    """Восстанавливает название подкатегории из callback_data (из индекса, если нужно)."""
    if callback_data.subcategory:
        return callback_data.subcategory

    category = _get_category_from_callback(callback_data)
    if callback_data.subcategory_index is not None and category:
        try:
            from catalog_data import CATALOG
            if category in CATALOG:
                all_subcategories = list(CATALOG[category].keys())
                if 0 <= callback_data.subcategory_index < len(all_subcategories):
                    return all_subcategories[callback_data.subcategory_index]
        except ImportError:
            pass
    
    return None


def _get_line_from_callback(callback_data: MenuCallback) -> str:
    """Восстанавливает линейку из callback_data (из индекса, если нужно)."""
    if callback_data.line:
        return callback_data.line
    if callback_data.line_index is not None:
        try:
            from catalog_data import CATALOG
            category = _get_category_from_callback(callback_data)
            if not category or category not in CATALOG:
                return None
            subcategory = _get_subcategory_from_callback(callback_data)
            # Протетика/Лаборатория: line в [subcategory][line]
            if subcategory and subcategory in CATALOG[category]:
                line_data = CATALOG[category][subcategory]
                if isinstance(line_data, dict):
                    all_lines = list(line_data.keys())
                    if 0 <= callback_data.line_index < len(all_lines):
                        return all_lines[callback_data.line_index]
            # Импланты: line в [category][line] (без subcategory)
            else:
                all_lines = list(CATALOG[category].keys())
                if 0 <= callback_data.line_index < len(all_lines):
                    return all_lines[callback_data.line_index]
        except ImportError:
            pass
    return None


def _get_product_from_callback(callback_data: MenuCallback) -> str:
    """Восстанавливает название продукта из callback_data (из индекса, если нужно)."""
    if callback_data.product:
        return callback_data.product

    category = _get_category_from_callback(callback_data)
    if callback_data.product_index is not None and category:
        try:
            from catalog_data import CATALOG
            if category not in CATALOG:
                return None
            cat = CATALOG[category]
            subcategory = _get_subcategory_from_callback(callback_data)
            line = _get_line_from_callback(callback_data)
            # Протетика/Лаборатория/Наборы/материалы: товары лежат в [subcategory][line], не в [subcategory]
            if subcategory and subcategory in cat and line:
                line_data = cat[subcategory].get(line) if isinstance(cat[subcategory], dict) else None
                if isinstance(line_data, dict):
                    all_products = [k for k in line_data.keys() if k != "no_size"]
                    if 0 <= callback_data.product_index < len(all_products):
                        return all_products[callback_data.product_index]
            # Импланты и старая структура: продукт = линейка (не используется для product_index)
            if not subcategory or subcategory not in cat:
                all_products = list(cat.keys())
                if 0 <= callback_data.product_index < len(all_products):
                    return all_products[callback_data.product_index]
        except ImportError:
            pass
    
    return None


def _catalog_log_ctx(callback_data: "MenuCallback") -> dict:
    """Извлекает контекст callback_data для логирования (все непустые поля + разрешённые значения)."""
    if not callback_data:
        return {}
    ctx = {}
    for k in ("level", "category", "category_index", "subcategory", "subcategory_index", "line", "line_index",
              "product", "product_index", "product_type", "product_type_str", "diameter", "length", "height",
              "product_name", "action"):
        v = getattr(callback_data, k, None)
        if v is not None:
            ctx[k] = v
    category = _get_category_from_callback(callback_data)
    if category and ctx.get("category_index") is not None:
        ctx["category_resolved"] = category
    subcategory = _get_subcategory_from_callback(callback_data)
    if subcategory and ctx.get("subcategory_index") is not None:
        ctx["subcategory_resolved"] = subcategory
    line = _get_line_from_callback(callback_data)
    if line and ctx.get("line_index") is not None:
        ctx["line_resolved"] = line
    product = _get_product_from_callback(callback_data)
    if product and ctx.get("product_index") is not None:
        ctx["product_resolved"] = product
    return ctx


def _log_catalog(user_id: int, handler: str, payload: str, callback_data: "MenuCallback" = None, show: str = None, **extra):
    """Логирование навигации по каталогу для отладки и сравнения с ожидаемой логикой."""
    parts = [f"catalog user={user_id} handler={handler} payload={payload!r}"]
    if callback_data is not None:
        ctx = _catalog_log_ctx(callback_data)
        if ctx:
            parts.append("ctx=" + str(ctx))
    if show:
        parts.append(f"show={show!r}")
    if extra:
        parts.append(" ".join(f"{k}={v!r}" for k, v in extra.items()))
    logger.info(" ".join(parts))


# Helper to check permissions
async def is_manager(user_id: int, session: AsyncSession):
    """Проверка прав менеджера с использованием кеша."""
    # Админы могут тестировать любые панели
    if user_id in config.ADMIN_IDS_LIST:
        return True
    user = await get_user_by_telegram_id(session, user_id, use_cache=True)
    return user and user.role == UserRole.MANAGER and user.is_active

@router.message(Command("menu"))
async def cmd_menu(message: types.Message, state: FSMContext, session: AsyncSession):
    if not await is_manager(message.from_user.id, session):
        return
    _log_catalog(message.from_user.id, "cmd_menu", "menu", show="categories")
    await message.answer("Каталог продукции:", reply_markup=make_categories_kb())
    await state.set_state(ManagerOrderState.browsing)

@router.callback_query(F.data == "manager:catalog")
async def manager_menu_catalog(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    """Открыть каталог продукции"""
    if not await is_manager(callback.from_user.id, session):
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    _log_catalog(callback.from_user.id, "manager_menu_catalog", callback.data, show="categories")
    await callback.message.edit_text("Каталог продукции:", reply_markup=make_categories_kb())
    await state.set_state(ManagerOrderState.browsing)
    await callback.answer()

@router.callback_query(F.data == "manager:main")
async def manager_back_to_main(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    """Возврат в главное меню менеджера"""
    if not await is_manager(callback.from_user.id, session):
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    await callback.message.edit_text("Выберите действие:", reply_markup=get_manager_menu_kb())
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "manager:product_map")
async def manager_product_map(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    """Карта продукции — настраиваемое меню с файлами"""
    if not await is_manager(callback.from_user.id, session):
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    from product_map import get_product_map_keyboard
    kb, msg = get_product_map_keyboard(path=None)
    await callback.message.edit_text(msg, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("pmap:"))
async def product_map_navigate(callback: types.CallbackQuery, session: AsyncSession):
    """Навигация по карте продукции и отправка файлов"""
    if not await is_manager(callback.from_user.id, session):
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    data = callback.data
    if not data.startswith("pmap:"):
        await callback.answer()
        return
    payload = data[5:].strip()  # после "pmap:"
    from product_map import get_product_map_keyboard, resolve_file_path, get_file_path_by_index, PREFIX
    if payload.startswith("file:"):
        arg = payload[5:].strip()
        # При длинном пути используется индекс (число)
        if arg.isdigit():
            file_path = get_file_path_by_index(int(arg))
        else:
            file_path = resolve_file_path(arg)
        if file_path and file_path.exists():
            suffix = file_path.suffix.lower()
            try:
                if suffix == ".pdf":
                    await callback.message.answer_document(
                        types.FSInputFile(str(file_path)),
                        caption=f"📄 {file_path.name}"
                    )
                elif suffix in (".png", ".jpg", ".jpeg"):
                    await callback.message.answer_photo(
                        types.FSInputFile(str(file_path)),
                        caption=f"🖼 {file_path.name}"
                    )
                else:
                    await callback.message.answer_document(
                        types.FSInputFile(str(file_path)),
                        caption=f"📎 {file_path.name}"
                    )
            except Exception as e:
                await callback.answer(f"Ошибка отправки файла: {e}", show_alert=True)
        else:
            await callback.answer("Файл не найден. Проверьте product_map_config.json и папку product_map_files/", show_alert=True)
        await callback.answer()
        return
    path = None
    if payload.startswith("back:"):
        path = payload[5:].strip() or None
    elif payload == "root":
        path = None
    else:
        path = payload
    kb, msg = get_product_map_keyboard(path=path)
    try:
        await callback.message.edit_text(msg, reply_markup=kb)
    except TelegramBadRequest:
        pass
    await callback.answer()


# --- Navigation Handlers ---

@router.callback_query(MenuCallback.filter(F.level == 0))
async def nav_categories(callback: types.CallbackQuery, callback_data: MenuCallback, state: FSMContext):
    # show_all_categories — дополнительные категории; back_to_main_categories — главный каталог
    show_all = callback_data.action == "show_all_categories"
    _log_catalog(callback.from_user.id, "nav_categories", callback.data, callback_data=callback_data,
                 show="categories" + ("_additional" if show_all else "_main"))
    
    # show_all=True: только дополнительные (Лаборатория, Наборы, материалы)
    # show_all=False: главные (Импланты, Протетика) + кнопка Дополнительно
    await callback.message.edit_text("Каталог продукции:", reply_markup=make_categories_kb(show_all=show_all))
    await state.set_state(ManagerOrderState.browsing)
    await callback.answer()

@router.callback_query(MenuCallback.filter(F.level == 1))
async def nav_lines(callback: types.CallbackQuery, callback_data: MenuCallback):
    show_all = callback_data.action in ["show_all_lines", "show_all_products", "show_all_subcategories"]
    if callback_data.action == "subcategory":
        show = "lines_for_subcategory"
    elif callback_data.category in ["Протетика", "Лаборатория", "Наборы", "материалы"]:
        show = "subcategories"
    else:
        show = "lines"
    _log_catalog(callback.from_user.id, "nav_lines", callback.data, callback_data=callback_data, show=show)
    
    # Если action == "show_all_lines", "show_all_products" или "show_all_subcategories", показываем все элементы
    try:
        # Если это подкатегория (action == "subcategory") или show_all_lines из подкатегории
        subcategory = _get_subcategory_from_callback(callback_data)
        if callback_data.action == "subcategory" or (
            callback_data.action == "show_all_lines" and subcategory and callback_data.category in ["Протетика", "Лаборатория", "Наборы", "материалы"]
        ):
            from keyboards.manager_kbs import make_lines_for_subcategory_kb
            if not subcategory:
                await callback.answer("Ошибка: подкатегория не найдена", show_alert=True)
                return
            
            await callback.message.edit_text(
                f"Категория: {callback_data.category}\nПодкатегория: {subcategory}\nВыберите линейку импланта:",
                reply_markup=make_lines_for_subcategory_kb(callback_data.category, subcategory, show_all=show_all)
            )
        elif callback_data.category in ["Протетика", "Лаборатория", "Наборы", "материалы"]:
            # Для протетики/лаборатории/наборов/материалов показываем подкатегории (Category), затем линейки
            await callback.message.edit_text(f"Категория: {callback_data.category}\nВыберите подкатегорию:", 
                                             reply_markup=make_lines_kb(callback_data.category, show_all=show_all))
        else:
            # Для остальных категорий показываем линейки
            await callback.message.edit_text(f"Категория: {callback_data.category}\nВыберите линейку:", 
                                             reply_markup=make_lines_kb(callback_data.category, show_all=show_all))
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            raise
    await callback.answer()

@router.callback_query(MenuCallback.filter(F.level == 2))
async def nav_diameters_or_product_lines(callback: types.CallbackQuery, callback_data: MenuCallback):
    """Для протетики/лаборатории/наборов — выбор типа после линейки. Для имплантов — выбор диаметра. Навигация: категория → линейка → тип → диаметр → длина → длина абатмента."""
    if callback_data.category in ["Протетика", "Лаборатория"]:
        show = "types"
    elif callback_data.category in ["Наборы", "материалы"]:
        show = "products"
    else:
        show = "diameters"
    _log_catalog(callback.from_user.id, "nav_diameters_or_product_lines", callback.data,
                 callback_data=callback_data, show=show)
    
    if callback_data.category in ["Протетика", "Лаборатория"]:
        # Протетика/Лаборатория: подкатегория → линейка → тип → диаметр → длина → высота абатмента → в корзину (без выбора наименования; наименование из каталога для наряда)
        from keyboards.manager_kbs import make_prosthetics_types_for_line_kb
        subcategory = _get_subcategory_from_callback(callback_data)
        await callback.message.edit_text(
            f"Линейка: {callback_data.line}\nВыберите угол (тип):",
            reply_markup=make_prosthetics_types_for_line_kb(callback_data.category, subcategory, callback_data.line)
        )
    elif callback_data.category in ["Наборы", "материалы"]:
        from keyboards.manager_kbs import make_products_for_line_kb
        show_all = callback_data.action == "show_all_products"
        subcategory = _get_subcategory_from_callback(callback_data)
        await callback.message.edit_text(
            f"Линейка: {callback_data.line}\nВыберите товар:",
            reply_markup=make_products_for_line_kb(callback_data.category, callback_data.line, show_all=show_all, subcategory=subcategory)
        )
    else:
        # Для имплантов - показываем диаметры
        await callback.message.edit_text(
            f"Линейка: {callback_data.line}\nВыберите:", 
            reply_markup=make_diameters_kb(callback_data.category, callback_data.line)
        )
    await callback.answer()

@router.callback_query(MenuCallback.filter((F.level == 3) & (F.product == None) & ((F.product_type != None) | (F.product_type_str != None))))
async def nav_prosthetics_type_selected(callback: types.CallbackQuery, callback_data: MenuCallback):
    """Протетика/Лаборатория: после выбора типа (угла или [N]) — показываем диаметры."""
    if callback_data.category not in ["Протетика", "Лаборатория"]:
        return
    pt_key = _get_product_type_key(callback_data)
    type_label = f"{pt_key}°" if isinstance(pt_key, (int, float)) else str(pt_key)
    _log_catalog(callback.from_user.id, "nav_prosthetics_type_selected", callback.data,
                 callback_data=callback_data, show="diameters")
    from keyboards.manager_kbs import make_prosthetics_diameters_for_line_kb
    subcategory = _get_subcategory_from_callback(callback_data)
    await callback.message.edit_text(
        f"Линейка: {callback_data.line}\nТип: {type_label}\nВыберите диаметр:",
        reply_markup=make_prosthetics_diameters_for_line_kb(
            callback_data.category, subcategory, callback_data.line,
            callback_data.product_type, callback_data.product_type_str
        )
    )
    await callback.answer()

@router.callback_query(MenuCallback.filter((F.level == 3) & (F.product == None)))
async def nav_products_or_items(callback: types.CallbackQuery, callback_data: MenuCallback):
    """Для имплантов - выбор длины после выбора диаметра."""
    _log_catalog(callback.from_user.id, "nav_products_or_items", callback.data,
                 callback_data=callback_data, show="lengths")
    try:
        # Для имплантов - показываем длины
        diam_body = getattr(callback_data, "diameter_body", None)
        stock = await get_stock(callback_data.line, callback_data.diameter, diam_body)
        if not stock:
            logger.warning(
                "catalog user=%s nav_products_or_items empty_stock line=%r diameter=%s",
                callback.from_user.id, callback_data.line, callback_data.diameter
            )
        sku_prefix = f"{callback_data.line} {_fmt_impl_diameter(callback_data.diameter, diam_body)}"
        await callback.message.edit_text(
            f"Товары {sku_prefix}:\nВыберите длину:",
            reply_markup=make_items_kb(
                callback_data.category,
                callback_data.line,
                callback_data.diameter,
                stock,
                diameter_body=diam_body
            )
        )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            raise
    await callback.answer()

@router.callback_query(MenuCallback.filter((F.level == 3) & (F.product != None) & (F.product_type == None)))
async def nav_product_type(callback: types.CallbackQuery, callback_data: MenuCallback):
    """Выбор типа для товара протетики/лаборатории/наборов после выбора линейки"""
    from catalog_data import CATALOG
    
    # Восстанавливаем product из индекса, если нужно
    product = _get_product_from_callback(callback_data)
    
    if not product:
        await callback.answer("Ошибка: товар не найден", show_alert=True)
        return
    
    _log_catalog(callback.from_user.id, "nav_product_type", callback.data,
                 callback_data=callback_data, show="product_types", product=product)
    # Проверяем, что это протетика/лаборатория/наборы
    if callback_data.category not in ["Протетика", "Лаборатория", "Наборы", "материалы"]:
        await callback.answer("Ошибка навигации", show_alert=True)
        return
    
    subcategory = _get_subcategory_from_callback(callback_data)
    await callback.message.edit_text(
        f"Тип: {product}\nЛинейка импланта: {callback_data.line}\nВыберите угол:",
        reply_markup=make_product_type_kb(callback_data.category, callback_data.line, product, subcategory=subcategory)
    )
    await callback.answer()

@router.callback_query(MenuCallback.filter((F.level == 4) & (F.product == None) & ((F.product_type != None) | (F.product_type_str != None)) & (F.diameter != None)))
async def nav_prosthetics_diameter_selected(callback: types.CallbackQuery, callback_data: MenuCallback):
    """Протетика/Лаборатория: после выбора диаметра (без товара) — показываем длину (высота десны)."""
    if callback_data.category not in ["Протетика", "Лаборатория"]:
        return
    from catalog_data import CATALOG
    from keyboards.manager_kbs import make_prosthetics_gum_height_for_line_kb
    _log_catalog(callback.from_user.id, "nav_prosthetics_diameter_selected", callback.data,
                 callback_data=callback_data, show="gum_heights")
    category = _get_category_from_callback(callback_data)
    subcategory = _get_subcategory_from_callback(callback_data)
    line = _get_line_from_callback(callback_data)
    line_data = CATALOG.get(category, {}).get(subcategory, {}).get(line, {}) if subcategory else {}
    stock_data = {}
    diam = callback_data.diameter
    pt = _get_product_type_key(callback_data)
    if isinstance(line_data, dict):
        for product_key, product_line_data in line_data.items():
            if product_key == "no_size" or not isinstance(product_line_data, dict):
                continue
            pd = product_line_data
            level1 = _catalog_get(pd, pt) or _catalog_get(pd, diam)
            if not isinstance(level1, dict):
                continue
            level2 = _catalog_get(level1, diam) if pt is not None else level1
            if not isinstance(level2, dict):
                level2 = level1
            for length in level2.keys():
                try:
                    length_f = float(length)
                except (ValueError, TypeError):
                    continue
                ld = _catalog_get(level2, length)
                if getattr(config, "USE_CATALOG_STOCK", False) and isinstance(ld, dict):
                    try:
                        from services.catalog_stock import get_qty
                        for h, info in ld.items():
                            if isinstance(info, dict) and info.get("sku"):
                                stock_data[length_f] = stock_data.get(length_f, 0) + get_qty(info["sku"])
                        if not stock_data.get(length_f) and ld.get("sku"):
                            stock_data[length_f] = stock_data.get(length_f, 0) + get_qty(ld["sku"])
                    except Exception:
                        stock_data[length_f] = stock_data.get(length_f, 0) + 10
                else:
                    stock_data[length_f] = stock_data.get(length_f, 0) + 10
    await callback.message.edit_text(
        f"Линейка: {line}\nУгол: {callback_data.product_type}°\nДиаметр: Ø{callback_data.diameter}\nВыберите длину (высота десны):",
        reply_markup=make_prosthetics_gum_height_for_line_kb(
            category, subcategory, line,
            callback_data.product_type, callback_data.diameter, stock_data,
            product_type_str=callback_data.product_type_str
        )
    )
    await callback.answer()

@router.callback_query(MenuCallback.filter((F.level == 4) & (F.action != "add_to_cart")))
async def nav_prosthetics_diameters(callback: types.CallbackQuery, callback_data: MenuCallback):
    """Выбор диаметра для протетики после выбора типа (при выборе по товару). add_to_cart обрабатывает prompt_quantity."""
    product = _get_product_from_callback(callback_data)
    if not product:
        await callback.answer("Ошибка: товар не найден", show_alert=True)
        return
    
    _log_catalog(callback.from_user.id, "nav_prosthetics_diameters", callback.data,
                 callback_data=callback_data, show="diameters", product=product)
    subcategory = _get_subcategory_from_callback(callback_data)
    await callback.message.edit_text(
        f"Тип: {product}\nУгол: {callback_data.product_type}°\nВыберите диаметр:" if callback_data.product_type is not None else f"Тип: {product}\nВыберите диаметр:",
        reply_markup=make_prosthetics_diameters_kb(callback_data.category, callback_data.line, product, callback_data.product_type, subcategory=subcategory)
    )
    await callback.answer()

@router.callback_query(MenuCallback.filter(F.level == 5) & (F.action != "select_abutment_height"))
async def nav_prosthetics_gum_height(callback: types.CallbackQuery, callback_data: MenuCallback):
    """Выбор высоты десны для протетики после выбора диаметра (при выборе по товару). select_abutment_height обрабатывает nav_prosthetics_abutment_height."""
    product = _get_product_from_callback(callback_data)
    if not product:
        await callback.answer("Ошибка: товар не найден", show_alert=True)
        return
    
    _log_catalog(callback.from_user.id, "nav_prosthetics_gum_height", callback.data,
                 callback_data=callback_data, show="gum_heights", product=product)
    stock = await get_stock(product, callback_data.diameter)
    if not stock:
        logger.warning(
            "catalog user=%s nav_prosthetics_gum_height empty_stock product=%r diameter=%s",
            callback.from_user.id, product, callback_data.diameter
        )
    subcategory = _get_subcategory_from_callback(callback_data)
    await callback.message.edit_text(
        f"Тип: {product}\nУгол: {callback_data.product_type}°\nДиаметр: Ø{callback_data.diameter}\nВыберите длину (высота десны):" if callback_data.product_type is not None else f"Тип: {product}\nДиаметр: Ø{callback_data.diameter}\nВыберите длину (высота десны):",
        reply_markup=make_prosthetics_gum_height_kb(
            callback_data.category,
            callback_data.line,
            product,
            callback_data.product_type,
            callback_data.diameter,
            stock,
            subcategory=subcategory
        )
    )
    await callback.answer()

@router.callback_query(MenuCallback.filter(F.action == "select_abutment_height"))
async def nav_prosthetics_abutment_height(callback: types.CallbackQuery, callback_data: MenuCallback):
    """Выбор высоты абатмента для протетики после выбора высоты десны."""
    from catalog_data import CATALOG
    from keyboards.manager_kbs import make_prosthetics_abutment_height_for_line_kb

    category = _get_category_from_callback(callback_data)
    subcategory = _get_subcategory_from_callback(callback_data)
    line = _get_line_from_callback(callback_data)
    line_data = CATALOG.get(category, {}).get(subcategory, {}).get(line, {}) if subcategory else {}

    # Поток без выбора товара: product_type, diameter, length заданы, product не задан
    if not callback_data.product and category in ["Протетика", "Лаборатория"] and (callback_data.product_type is not None or callback_data.product_type_str):
        _log_catalog(callback.from_user.id, "nav_prosthetics_abutment_height_line", callback.data,
                     callback_data=callback_data, show="abutment_heights")
        stock = {}
        pt = _get_product_type_key(callback_data)
        diam, length = callback_data.diameter, callback_data.length
        if isinstance(line_data, dict):
            for product_key, product_line_data in line_data.items():
                if product_key == "no_size" or not isinstance(product_line_data, dict):
                    continue
                pd = product_line_data
                level1 = _catalog_get(pd, pt) or _catalog_get(pd, diam)
                if not isinstance(level1, dict):
                    continue
                level2 = _catalog_get(level1, diam) if pt is not None else level1
                if not isinstance(level2, dict):
                    level2 = level1
                ld = _catalog_get(level2, length)
                if isinstance(ld, dict):
                    for height, info in ld.items():
                        if isinstance(info, dict) and info.get("sku"):
                            try:
                                h_f = float(height)
                                if getattr(config, "USE_CATALOG_STOCK", False):
                                    try:
                                        from services.catalog_stock import get_qty
                                        stock[h_f] = stock.get(h_f, 0) + get_qty(info["sku"])
                                    except Exception:
                                        stock[h_f] = stock.get(h_f, 0) + 10
                                else:
                                    stock[h_f] = stock.get(h_f, 0) + 10
                            except (ValueError, TypeError):
                                pass
        await callback.message.edit_text(
            f"Линейка: {line}\nУгол: {callback_data.product_type}°\nДиаметр: Ø{callback_data.diameter}\n"
            f"Длина (высота десны): {callback_data.length} мм\nВыберите длину абатмента:",
            reply_markup=make_prosthetics_abutment_height_for_line_kb(
                category, subcategory, line,
                callback_data.product_type, callback_data.diameter, callback_data.length, stock,
                product_type_str=callback_data.product_type_str
            )
        )
        await callback.answer()
        return
    
    product = _get_product_from_callback(callback_data)
    if not product:
        await callback.answer("Ошибка: товар не найден", show_alert=True)
        return
    
    _log_catalog(callback.from_user.id, "nav_prosthetics_abutment_height", callback.data,
                 callback_data=callback_data, show="abutment_heights", product=product)
    # Структура: category -> Category (subcategory) -> Sub_category (line) -> product -> type -> diameter -> gum_height -> abutment_height
    stock = {}
    product_data = line_data.get(product) if isinstance(line_data, dict) and product in line_data else None
    
    if product_data:
        type_level = _catalog_get(product_data, callback_data.product_type) if callback_data.product_type is not None else None
        if type_level is not None:
            diam_level = _catalog_get(type_level, callback_data.diameter)
            if diam_level is not None:
                heights_data = _catalog_get(diam_level, callback_data.length)
                if isinstance(heights_data, dict):
                    for height, product_info in heights_data.items():
                        if isinstance(height, (int, float)) and isinstance(product_info, dict) and "sku" in product_info:
                            if getattr(config, "USE_CATALOG_STOCK", False):
                                try:
                                    from services.catalog_stock import get_qty
                                    stock[height] = get_qty(product_info["sku"])
                                except Exception:
                                    stock[height] = 0
                            else:
                                stock[height] = 10
        elif not callback_data.product_type:
            diam_level = _catalog_get(product_data, callback_data.diameter)
            if diam_level is not None:
                heights_data = _catalog_get(diam_level, callback_data.length)
                if isinstance(heights_data, dict):
                    for height, product_info in heights_data.items():
                        if isinstance(height, (int, float)) and isinstance(product_info, dict) and "sku" in product_info:
                            if getattr(config, "USE_CATALOG_STOCK", False):
                                try:
                                    from services.catalog_stock import get_qty
                                    stock[height] = get_qty(product_info["sku"])
                                except Exception:
                                    stock[height] = 0
                            else:
                                stock[height] = 10
    
    if not stock:
        logger.warning(
            "catalog user=%s nav_prosthetics_abutment_height empty_heights category=%r product=%r line=%r type=%r diam=%s gum=%s",
            callback.from_user.id, callback_data.category, product, callback_data.line,
            callback_data.product_type, callback_data.diameter, callback_data.length
        )
    await callback.message.edit_text(
        f"Тип: {product}\nУгол: {callback_data.product_type}°\n" if callback_data.product_type is not None else f"Тип: {product}\n"
        f"Диаметр: Ø{callback_data.diameter}\nДлина (высота десны): {callback_data.length} мм\n"
        f"Выберите длину абатмента:",
        reply_markup=make_prosthetics_abutment_height_kb(
            callback_data.category,
            callback_data.line,
            product,
            callback_data.product_type,
            callback_data.diameter,
            callback_data.length,
            stock,
            subcategory=subcategory
        )
    )
    await callback.answer()

@router.callback_query(MenuCallback.filter((F.level == 5) & (F.action == "no_size_list")))
async def nav_no_size_items(callback: types.CallbackQuery, callback_data: MenuCallback):
    """Показывает список товаров без размеров"""
    category = _get_category_from_callback(callback_data)
    line = _get_line_from_callback(callback_data)
    _log_catalog(callback.from_user.id, "nav_no_size_items", callback.data,
                 callback_data=callback_data, show="no_size_items")
    stock = {}
    if getattr(config, "USE_CATALOG_STOCK", False) and category and line:
        try:
            from services.catalog_stock import get_stock_no_size
            stock = get_stock_no_size(category, line)
        except Exception:
            pass
    await callback.message.edit_text(
        f"Линейка: {line}\nВыберите тип:",
        reply_markup=make_no_size_items_kb(category, line, stock)
    )
    await callback.answer()

# --- Add to Cart ---

@router.callback_query(F.data == "noop")
async def handle_noop(callback: types.CallbackQuery):
    """Кнопки «Нет в наличии» / «Нет товаров»."""
    _log_catalog(callback.from_user.id, "handle_noop", callback.data, show="noop")
    await callback.answer("Нет в наличии", show_alert=True)

@router.callback_query(MenuCallback.filter(F.action == "add_to_cart"))
async def prompt_quantity(callback: types.CallbackQuery, callback_data: MenuCallback, state: FSMContext):
    from catalog_data import CATALOG
    
    _log_catalog(callback.from_user.id, "add_to_cart", callback.data, callback_data=callback_data, show="prompt_quantity")
    # Протетика/Лаборатория: поток без выбора товара — наименование из каталога (как у имплантов) для наряда/склада/курьера
    pt_key = _get_product_type_key(callback_data)
    category = _get_category_from_callback(callback_data)
    subcategory = _get_subcategory_from_callback(callback_data)
    line = _get_line_from_callback(callback_data)
    if (category in ["Протетика", "Лаборатория"] and not callback_data.product and
            pt_key is not None and callback_data.diameter is not None and
            callback_data.length is not None and callback_data.height is not None):
        line_data = CATALOG.get(category, {}).get(subcategory, {}).get(line, {}) if subcategory else {}
        product_data = None
        if isinstance(line_data, dict):
            def _find_product(pd, pt, d, l, h):
                # Структура с product_type: product -> type -> diameter -> length -> height
                if pt is not None:
                    l1 = _catalog_get(pd, pt)
                    if l1 is not None and isinstance(l1, dict):
                        l2 = _catalog_get(l1, d)
                        if l2 is not None and isinstance(l2, dict):
                            l3 = _catalog_get(l2, l)
                            if l3 is not None and isinstance(l3, dict):
                                res = _catalog_get(l3, h)
                                if res is not None:
                                    return res
                # Структура без product_type (когда type=0): product -> diameter -> length -> height
                l1 = _catalog_get(pd, d)
                if l1 is None or not isinstance(l1, dict):
                    return None
                l2 = _catalog_get(l1, l)
                if l2 is None or not isinstance(l2, dict):
                    return None
                return _catalog_get(l2, h)
            for product_key, product_line_data in line_data.items():
                if product_key == "no_size" or not isinstance(product_line_data, dict):
                    continue
                product_data = _find_product(
                    product_line_data,
                    pt_key,
                    callback_data.diameter,
                    callback_data.length,
                    callback_data.height
                )
                if product_data:
                    break
        if not product_data or not isinstance(product_data, dict):
            logger.warning(
                "catalog user=%s add_to_cart prosthetics_line not_found type=%s diam=%s len=%s height=%s",
                callback.from_user.id, callback_data.product_type, callback_data.diameter,
                callback_data.length, callback_data.height
            )
            product_data = {
                "name": f"{line} Ø{callback_data.diameter} Д{callback_data.length} А{callback_data.height}",
                "sku": f"P-{callback_data.diameter}-{callback_data.length}-{callback_data.height}",
                "unit": "шт"
            }
        logger.info(
            "catalog user=%s add_to_cart branch=prosthetics_line name=%r sku=%r",
            callback.from_user.id, product_data.get("name"), product_data.get("sku")
        )
        await state.update_data(current_selection={
            'category': category,
            'line': line,
            'product': None,
            'product_type': callback_data.product_type,
            'diameter': callback_data.diameter,
            'length': callback_data.length,
            'height': callback_data.height,
            'name': product_data.get("name", ""),
            'sku': product_data.get("sku", ""),
            'unit': product_data.get("unit", "шт"),
            'no_size': False
        })
        await state.set_state(ManagerOrderState.waiting_for_quantity)
        await callback.message.answer(
            f"Выберите количество для {product_data.get('name', '')}:",
            reply_markup=make_quantity_kb(max_quantity=20)
        )
        await callback.answer()
        return
    if callback_data.product_name or (callback_data.product_index is not None and callback_data.action == "add_to_cart"):
        # Товар без размеров - получаем данные из каталога (product_name или product_index)
        product_name = callback_data.product_name
        if not product_name and callback_data.product_index is not None:
            line_block = CATALOG.get(category, {}).get(subcategory, {}) if subcategory else {}
            line_data = line_block.get(line, {}) if isinstance(line_block, dict) else {}
            if isinstance(line_data, dict):
                all_products = [k for k in line_data.keys() if k != "no_size"]
                for item in line_data.get("no_size", []):
                    if isinstance(item, dict) and item.get("name") and item["name"] not in all_products:
                        all_products.append(item["name"])
                if 0 <= callback_data.product_index < len(all_products):
                    product_name = all_products[callback_data.product_index]
        if not product_name:
            await callback.answer("Ошибка: товар не найден", show_alert=True)
            return
        product_data = None
        if category and category in CATALOG:
            no_size_items = None
            # Протетика/Лаборатория/Наборы/материалы: category -> subcategory -> line -> no_size
            if category in ["Протетика", "Лаборатория", "Наборы", "материалы"]:
                if subcategory and subcategory in CATALOG[category]:
                    line_block = CATALOG[category][subcategory]
                    if isinstance(line_block, dict) and line and line in line_block:
                        line_data = line_block[line]
                        if isinstance(line_data, dict) and "no_size" in line_data:
                            no_size_items = line_data["no_size"]
            else:
                # Импланты: category -> line -> no_size
                if line and line in CATALOG[category]:
                    line_block = CATALOG[category][line]
                    if isinstance(line_block, dict) and "no_size" in line_block:
                        no_size_items = line_block["no_size"]
            if isinstance(no_size_items, list):
                for item in no_size_items:
                    if isinstance(item, dict) and item.get("name") == product_name:
                        product_data = item
                        break
                    elif isinstance(item, str) and item == product_name:
                        product_data = {"name": item, "sku": item, "unit": "шт"}
                        break
        
        if not product_data:
            logger.warning(
                "catalog user=%s add_to_cart no_size not_in_catalog product_name=%r cat=%r line=%r",
                callback.from_user.id, product_name, category, line
            )
            product_data = {"name": product_name, "sku": product_name, "unit": "шт"}
        
        logger.info(
            "catalog user=%s add_to_cart branch=no_size name=%r sku=%r",
            callback.from_user.id, product_data["name"], product_data["sku"]
        )
        await state.update_data(current_selection={
            'category': category,
            'line': line,
            'product_name': product_name,
            'name': product_data["name"],
            'sku': product_data["sku"],  # Артикул из 1C
            'unit': product_data.get("unit", "шт"),
            'no_size': True
        })
        await callback.message.answer(
            f"Выберите количество для {product_data['name']}:",
            reply_markup=make_quantity_kb(max_quantity=20)
        )
    elif category in ["Протетика", "Лаборатория"]:
        # Восстанавливаем product из индекса, если нужно
        product = _get_product_from_callback(callback_data)
        if not product or not callback_data.height:
            await callback.answer("Ошибка: данные товара неполные", show_alert=True)
            return

        # Протетика/Лаборатория: category -> Category (subcategory) -> Sub_category (line) -> product -> type -> diameter -> gum_height -> abutment_height
        product_data = None
        line_data = CATALOG.get(category, {}).get(subcategory, {}).get(line, {}) if subcategory else {}
        product_line_data = line_data.get(product) if isinstance(line_data, dict) and product in line_data else None
        
        if product_line_data:
            if callback_data.product_type is not None:
                type_level = _catalog_get(product_line_data, callback_data.product_type)
                if type_level is not None:
                    diam_level = _catalog_get(type_level, callback_data.diameter)
                    if diam_level is not None:
                        length_level = _catalog_get(diam_level, callback_data.length)
                        if length_level is not None:
                            product_data = _catalog_get(length_level, callback_data.height)
            elif callback_data.diameter is not None:
                diam_level = _catalog_get(product_line_data, callback_data.diameter)
                if diam_level is not None:
                    length_level = _catalog_get(diam_level, callback_data.length)
                    if length_level is not None:
                        product_data = _catalog_get(length_level, callback_data.height)
        
        if not product_data:
            logger.warning(
                "catalog user=%s add_to_cart prosthetics not_in_catalog product=%r line=%r type=%r diam=%s gum=%s abut=%s",
                callback.from_user.id, product, callback_data.line, callback_data.product_type,
                callback_data.diameter, callback_data.length, callback_data.height
            )
            type_str = f" {callback_data.product_type}" if callback_data.product_type else ""
            product_data = {
                "name": f"{product}{type_str} Ø{callback_data.diameter} Д{callback_data.length} А{callback_data.height}",
                "sku": f"{product[:3].upper()}-{callback_data.diameter}-{callback_data.length}-{callback_data.height}",
                "unit": "шт"
            }
        
        logger.info(
            "catalog user=%s add_to_cart branch=prosthetics name=%r sku=%r",
            callback.from_user.id, product_data["name"], product_data["sku"]
        )
        await state.update_data(current_selection={
            'category': callback_data.category,
            'line': callback_data.line,  # Линейка импланта
            'product': product,  # Название товара
            'product_type': callback_data.product_type,
            'diameter': callback_data.diameter,
            'length': callback_data.length,  # Длина (высота десны)
            'height': callback_data.height,  # Высота абатмента
            'name': product_data["name"],
            'sku': product_data["sku"],  # Артикул из 1C
            'unit': product_data.get("unit", "шт"),
            'no_size': False
        })
        await callback.message.answer(
            f"Выберите количество для {product_data['name']}:",
            reply_markup=make_quantity_kb(max_quantity=20)
        )
    else:
        # Товар с размерами (импланты) - получаем данные из каталога
        # category, line уже разрешены из _get_category_from_callback, _get_line_from_callback (поддержка индексов)
        diam_body = getattr(callback_data, "diameter_body", None)
        diam_key = (callback_data.diameter, diam_body) if diam_body is not None else callback_data.diameter
        product_data = None
        if (category in CATALOG and 
            line in CATALOG[category] and
            diam_key in CATALOG[category][line] and
            callback_data.length in CATALOG[category][line][diam_key]):
            product_data = CATALOG[category][line][diam_key][callback_data.length]
        
        if not product_data:
            logger.warning(
                "catalog user=%s add_to_cart implants not_in_catalog line=%r diameter=%s length=%s",
                callback.from_user.id, line, callback_data.diameter, callback_data.length
            )
            product_data = {
                "name": f"{line} {_fmt_impl_diameter(callback_data.diameter, diam_body)} L{callback_data.length}",
                "sku": get_sku(line, callback_data.diameter, callback_data.length),
                "unit": "шт"
            }
        
        logger.info(
            "catalog user=%s add_to_cart branch=implants name=%r sku=%r",
            callback.from_user.id, product_data["name"], product_data["sku"]
        )
        sel = {
            'category': category,
            'line': line,
            'diameter': callback_data.diameter,
            'length': callback_data.length,
            'name': product_data["name"],
            'sku': product_data["sku"],  # Артикул из 1C
            'unit': product_data.get("unit", "шт"),
            'no_size': False
        }
        if diam_body is not None:
            sel['diameter_body'] = diam_body
        await state.update_data(current_selection=sel)
        await callback.message.answer(
            f"Выберите количество для {product_data['name']}:",
            reply_markup=make_quantity_kb(max_quantity=20)
        )
    
    await state.set_state(ManagerOrderState.waiting_for_quantity)
    await callback.answer()

@router.callback_query(MenuCallback.filter((F.level == 98) & (F.action == "select_quantity")), ManagerOrderState.waiting_for_quantity)
async def process_quantity_callback(callback: types.CallbackQuery, callback_data: MenuCallback, state: FSMContext):
    """Обработка выбора количества через кнопки."""
    user_id = callback.from_user.id if callback.from_user else 0
    qty = callback_data.item_index  # Количество из callback_data
    
    if not qty or qty < 1:
        await callback.answer("❌ Неверное количество", show_alert=True)
        return
    
    data = await state.get_data()
    item = data.get('current_selection')
    if not item:
        logger.warning("catalog user=%s process_quantity_callback no_current_selection qty=%s", user_id, qty)
        await callback.answer("Ошибка состояния. Начните заново.", show_alert=True)
        await state.clear()
        return

    logger.info(
        "catalog user=%s process_quantity_callback qty=%s name=%r sku=%r no_size=%s",
        user_id, qty, item.get("name"), item.get("sku"), item.get("no_size")
    )

    # Validate stock availability (только для товаров с размерами)
    # Протетика/Лаборатория: остаток по артикулу (SKU). Импланты: остаток по длине (line + diameter + length).
    if not item.get('no_size'):
        if item.get('category') in ["Протетика", "Лаборатория"] and item.get('height') is not None:
            try:
                from services.catalog_stock import get_qty
                available_qty = get_qty(item['sku'])
            except Exception:
                available_qty = 999
        else:
            stock = await get_stock(item['line'], item['diameter'], item.get('diameter_body'))
            available_qty = stock.get(item['length'], 0)
        
        # Check current cart quantity for this SKU
        cart = data.get('cart', [])
        current_cart_qty = 0
        for cart_item in cart:
            if cart_item['sku'] == item['sku']:
                current_cart_qty = cart_item['quantity']
                break
        
        total_requested = current_cart_qty + qty
        
        if total_requested > available_qty:
            logger.warning(
                "catalog user=%s process_quantity_callback stock_fail sku=%r available=%s requested=%s in_cart=%s",
                user_id, item.get("sku"), available_qty, qty, current_cart_qty
            )
            await callback.answer(
                f"❌ Недостаточно товара на складе.\n"
                f"Доступно: {available_qty} шт.\n"
                f"Уже в корзине: {current_cart_qty} шт.\n"
                f"Максимум можно добавить: {max(0, available_qty - current_cart_qty)} шт.",
                show_alert=True
            )
            return
    else:
        cart = data.get('cart', [])
        # Для товаров без размеров — проверка остатков при USE_CATALOG_STOCK
        if getattr(config, "USE_CATALOG_STOCK", False):
            try:
                from services.catalog_stock import get_qty
                available_qty = get_qty(item['sku'])
                current_cart_qty = sum(c['quantity'] for c in cart if c['sku'] == item['sku'])
                if current_cart_qty + qty > available_qty:
                    logger.warning(
                        "catalog user=%s process_quantity_callback stock_fail no_size sku=%r available=%s requested=%s in_cart=%s",
                        user_id, item.get("sku"), available_qty, qty, current_cart_qty
                    )
                    await callback.answer(
                        f"❌ Недостаточно товара на складе.\n"
                        f"Доступно: {available_qty} шт.\n"
                        f"Уже в корзине: {current_cart_qty} шт.\n"
                        f"Максимум можно добавить: {max(0, available_qty - current_cart_qty)} шт.",
                        show_alert=True
                    )
                    return
            except Exception as e:
                logger.debug("catalog user=%s process_quantity_callback no_size stock check skipped: %s", user_id, e)

    item['quantity'] = qty
    
    # Add to cart list
    # Check if exists, update qty
    found = False
    cart = data.get('cart', [])
    for cart_item in cart:
        if cart_item['sku'] == item['sku']:
            cart_item['quantity'] += qty
            found = True
            break
    if not found:
        cart.append(item)
    
    await state.update_data(cart=cart)
    await state.set_state(ManagerOrderState.browsing)
    
    logger.info("catalog user=%s process_quantity_callback added name=%r sku=%r qty=%s cart_len=%s", user_id, item["name"], item["sku"], qty, len(cart))
    
    # Удаляем сообщение с кнопками количества
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    await callback.answer(f"✅ Добавлено: {item['name']} x{qty}")
    
    # Показываем сообщение с подтверждением и кнопкой корзины
    await callback.message.answer(
        f"✅ Товар добавлен в корзину:\n"
        f"{item['name']} x{qty}",
        reply_markup=get_manager_menu_kb()
    )

@router.callback_query(MenuCallback.filter((F.level == 99) & (F.action == "cancel_quantity")), ManagerOrderState.waiting_for_quantity)
async def cancel_quantity(callback: types.CallbackQuery, state: FSMContext):
    """Отмена выбора количества."""
    await state.set_state(ManagerOrderState.browsing)
    await state.update_data(current_selection=None)
    
    # Удаляем сообщение с кнопками количества
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    await callback.answer("❌ Выбор количества отменен")
    
    # Возвращаем в каталог
    await callback.message.answer("Каталог продукции:", reply_markup=make_categories_kb())

@router.message(ManagerOrderState.waiting_for_quantity)
async def process_quantity(message: types.Message, state: FSMContext):
    user_id = message.from_user.id if message.from_user else 0
    # Валидация через Pydantic
    try:
        from services.validation import QuantityInput
        quantity_input = QuantityInput.from_string(message.text)
        qty = quantity_input.quantity
    except ValueError as e:
        logger.warning("catalog user=%s process_quantity invalid_input=%r error=%s", user_id, message.text, str(e))
        await message.answer(f"❌ {str(e)}")
        return

    data = await state.get_data()
    item = data.get('current_selection')
    if not item:
        logger.warning("catalog user=%s process_quantity no_current_selection qty=%s", user_id, qty)
        await message.answer("Ошибка состояния. Начните заново.")
        return

    logger.info(
        "catalog user=%s process_quantity qty=%s name=%r sku=%r no_size=%s",
        user_id, qty, item.get("name"), item.get("sku"), item.get("no_size")
    )

    # Validate stock availability (только для товаров с размерами)
    # Протетика/Лаборатория: остаток по артикулу (SKU). Импланты: остаток по длине (line + diameter + length).
    if not item.get('no_size'):
        if item.get('category') in ["Протетика", "Лаборатория"] and item.get('height') is not None:
            try:
                from services.catalog_stock import get_qty
                available_qty = get_qty(item['sku'])
            except Exception:
                available_qty = 999
        else:
            stock = await get_stock(item['line'], item['diameter'], item.get('diameter_body'))
            available_qty = stock.get(item['length'], 0)
        
        # Check current cart quantity for this SKU
        cart = data.get('cart', [])
        current_cart_qty = 0
        for cart_item in cart:
            if cart_item['sku'] == item['sku']:
                current_cart_qty = cart_item['quantity']
                break
        
        total_requested = current_cart_qty + qty
        
        if total_requested > available_qty:
            logger.warning(
                "catalog user=%s process_quantity stock_fail sku=%r available=%s requested=%s in_cart=%s",
                user_id, item.get("sku"), available_qty, qty, current_cart_qty
            )
            await message.answer(
                f"❌ Недостаточно товара на складе.\n"
                f"Доступно: {available_qty} шт.\n"
                f"Уже в корзине: {current_cart_qty} шт.\n"
                f"Запрошено: {qty} шт.\n"
                f"Максимум можно добавить: {max(0, available_qty - current_cart_qty)} шт."
            )
            return
    else:
        cart = data.get('cart', [])
        # Для товаров без размеров — проверка остатков при USE_CATALOG_STOCK
        if getattr(config, "USE_CATALOG_STOCK", False):
            try:
                from services.catalog_stock import get_qty
                available_qty = get_qty(item['sku'])
                current_cart_qty = sum(c['quantity'] for c in cart if c['sku'] == item['sku'])
                if current_cart_qty + qty > available_qty:
                    logger.warning(
                        "catalog user=%s process_quantity stock_fail no_size sku=%r available=%s requested=%s in_cart=%s",
                        user_id, item.get("sku"), available_qty, qty, current_cart_qty
                    )
                    await message.answer(
                        f"❌ Недостаточно товара на складе.\n"
                        f"Доступно: {available_qty} шт.\n"
                        f"Уже в корзине: {current_cart_qty} шт.\n"
                        f"Максимум можно добавить: {max(0, available_qty - current_cart_qty)} шт."
                    )
                    return
            except Exception as e:
                logger.debug("catalog user=%s process_quantity no_size stock check skipped: %s", user_id, e)

    item['quantity'] = qty
    
    # Add to cart list
    # Check if exists, update qty
    found = False
    for cart_item in cart:
        if cart_item['sku'] == item['sku']:
            cart_item['quantity'] += qty
            found = True
            break
    if not found:
        cart.append(item)
    
    await state.update_data(cart=cart)
    logger.info("catalog user=%s process_quantity added name=%r sku=%r qty=%s cart_len=%s", user_id, item["name"], item["sku"], qty, len(cart))

    # Return to appropriate menu
    if item.get('no_size'):
        stock_ns = {}
        if getattr(config, "USE_CATALOG_STOCK", False):
            try:
                from services.catalog_stock import get_stock_no_size
                stock_ns = get_stock_no_size(item['category'], item['line'])
            except Exception:
                pass
        kb = make_no_size_items_kb(item['category'], item['line'], stock_ns)
    else:
        stock = await get_stock(item['line'], item['diameter'], item.get('diameter_body'))
        kb = make_items_kb(item['category'], item['line'], item['diameter'], stock, diameter_body=item.get('diameter_body'))
    
    await message.answer(f"✅ Добавлено: {item['name']} ({qty} шт).", reply_markup=kb)
    await state.set_state(ManagerOrderState.browsing)

# --- Cart Logic ---

@router.callback_query(MenuCallback.filter(F.action == "cart"))
async def view_cart(callback: types.CallbackQuery, callback_data: MenuCallback, state: FSMContext):
    data = await state.get_data()
    cart = data.get('cart', [])
    _log_catalog(callback.from_user.id, "view_cart", callback.data, callback_data=callback_data, show="cart", cart_len=len(cart))
    
    is_urgent = data.get('is_urgent', False)
    delivery_type = data.get('delivery_type', "courier")
    
    if not cart:
        await callback.answer("Корзина пуста", show_alert=True)
        return
    
    text = "🛒 *Корзина:*\n\n"
    total_qty = 0
    for idx, item in enumerate(cart, 1):
        text += f"{idx}. {item['name']} — {item['quantity']} шт.\n"
        total_qty += item['quantity']
        
    text += f"\nВсего: {total_qty} шт."
    
    await callback.message.edit_text(text, parse_mode="Markdown", 
                                     reply_markup=make_cart_kb(is_urgent, delivery_type, cart))
    await state.set_state(ManagerOrderState.cart_view)

@router.callback_query(MenuCallback.filter(F.action == "clear_cart"))
async def clear_cart(callback: types.CallbackQuery, callback_data: MenuCallback, state: FSMContext):
    data = await state.get_data()
    cart_len = len(data.get("cart", []))
    _log_catalog(callback.from_user.id, "clear_cart", callback.data, callback_data=callback_data, show="categories", cart_len=cart_len)
    await state.update_data(cart=[])
    await callback.message.edit_text("Корзина очищена.", reply_markup=make_categories_kb())
    await state.set_state(ManagerOrderState.browsing)
    await callback.answer()

@router.callback_query(MenuCallback.filter(F.action == "toggle_urgent"))
async def toggle_urgent(callback: types.CallbackQuery, callback_data: MenuCallback, state: FSMContext):
    data = await state.get_data()
    new_status = not data.get('is_urgent', False)
    await state.update_data(is_urgent=new_status)
    await view_cart(callback, callback_data, state)

@router.callback_query(MenuCallback.filter(F.action == "toggle_delivery"))
async def toggle_delivery(callback: types.CallbackQuery, callback_data: MenuCallback, state: FSMContext):
    data = await state.get_data()
    current = data.get('delivery_type', "courier")
    new = "taxi" if current == "courier" else "courier"
    await state.update_data(delivery_type=new)
    await view_cart(callback, callback_data, state)

@router.callback_query(MenuCallback.filter(F.action == "increase_qty"))
async def increase_quantity(callback: types.CallbackQuery, callback_data: MenuCallback, state: FSMContext):
    data = await state.get_data()
    cart = data.get('cart', [])
    item_index = callback_data.item_index
    _log_catalog(callback.from_user.id, "increase_qty", callback.data, callback_data=callback_data, show="cart", item_index=item_index, cart_len=len(cart))
    
    if item_index is None or item_index >= len(cart):
        logger.warning("catalog user=%s increase_qty bad item_index=%s cart_len=%s", callback.from_user.id, item_index, len(cart))
        await callback.answer("Ошибка: товар не найден", show_alert=True)
        return
    
    item = cart[item_index]
    
    # Validate stock. Протетика/Лаборатория: остаток по артикулу (SKU). Импланты: остаток по длине.
    if not item.get('no_size'):
        if item.get('category') in ["Протетика", "Лаборатория"] and item.get('height') is not None:
            try:
                from services.catalog_stock import get_qty
                available_qty = get_qty(item['sku'])
            except Exception:
                available_qty = 999
        else:
            stock = await get_stock(item['line'], item['diameter'], item.get('diameter_body'))
            available_qty = stock.get(item['length'], 0)
        if item['quantity'] >= available_qty:
            await callback.answer(f"❌ Максимальное количество: {available_qty} шт.", show_alert=True)
            return
    elif getattr(config, "USE_CATALOG_STOCK", False):
        try:
            from services.catalog_stock import get_qty
            available_qty = get_qty(item['sku'])
            if item['quantity'] >= available_qty:
                await callback.answer(f"❌ Максимальное количество: {available_qty} шт.", show_alert=True)
                return
        except Exception:
            pass
    
    cart[item_index]['quantity'] += 1
    await state.update_data(cart=cart)
    await view_cart(callback, callback_data, state)
    await callback.answer()

@router.callback_query(MenuCallback.filter(F.action == "decrease_qty"))
async def decrease_quantity(callback: types.CallbackQuery, callback_data: MenuCallback, state: FSMContext):
    data = await state.get_data()
    cart = data.get('cart', [])
    item_index = callback_data.item_index
    _log_catalog(callback.from_user.id, "decrease_qty", callback.data, callback_data=callback_data, show="cart", item_index=item_index, cart_len=len(cart))
    
    if item_index is None or item_index >= len(cart):
        logger.warning("catalog user=%s decrease_qty bad item_index=%s cart_len=%s", callback.from_user.id, item_index, len(cart))
        await callback.answer("Ошибка: товар не найден", show_alert=True)
        return
    
    if cart[item_index]['quantity'] <= 1:
        await callback.answer("❌ Минимальное количество: 1 шт. Используйте 'Удалить' для удаления.", show_alert=True)
        return
    
    cart[item_index]['quantity'] -= 1
    await state.update_data(cart=cart)
    await view_cart(callback, callback_data, state)
    await callback.answer()

@router.callback_query(MenuCallback.filter(F.action == "remove_item"))
async def remove_item(callback: types.CallbackQuery, callback_data: MenuCallback, state: FSMContext):
    data = await state.get_data()
    cart = data.get('cart', [])
    item_index = callback_data.item_index
    _log_catalog(callback.from_user.id, "remove_item", callback.data, callback_data=callback_data, show="cart", item_index=item_index, cart_len=len(cart))
    
    if item_index is None or item_index >= len(cart):
        logger.warning("catalog user=%s remove_item bad item_index=%s cart_len=%s", callback.from_user.id, item_index, len(cart))
        await callback.answer("Ошибка: товар не найден", show_alert=True)
        return
    
    removed_item = cart.pop(item_index)
    logger.info("catalog user=%s remove_item sku=%r name=%r", callback.from_user.id, removed_item.get("sku"), removed_item.get("name"))
    await state.update_data(cart=cart)
    
    if not cart:
        await callback.message.edit_text("Корзина очищена.", reply_markup=make_categories_kb())
        await state.set_state(ManagerOrderState.browsing)
    else:
        await view_cart(callback, callback_data, state)
    
    await callback.answer(f"✅ {removed_item['name']} удален из корзины")

@router.callback_query(MenuCallback.filter(F.action == "submit_order"))
async def start_submit_order(callback: types.CallbackQuery, callback_data: MenuCallback, state: FSMContext):
    data = await state.get_data()
    cart = data.get('cart', [])
    _log_catalog(callback.from_user.id, "submit_order", callback.data, callback_data=callback_data, show="submit", cart_len=len(cart))
    
    if not cart:
        await callback.answer("Корзина пуста!", show_alert=True)
        return

    # Check if clinic is already selected
    if data.get('selected_clinic_id'):
        await finalize_order(callback, state)
    else:
        # Start Clinic Search
        await callback.message.edit_text(
            "🔎 *Выбор клиники*\n\n"
            "Введите поисковый запрос:\n"
            "— Название клиники\n"
            "— ФИО врача\n"
            "— Номер телефона\n",
            parse_mode="Markdown"
        )
        await state.set_state(ManagerOrderState.waiting_for_clinic_search)

@router.message(ManagerOrderState.waiting_for_clinic_search)
async def process_clinic_search(message: types.Message, state: FSMContext, session: AsyncSession):
    """Обработка поиска клиники с валидацией."""
    try:
        from services.validation import SearchQueryInput
        search_input = SearchQueryInput.from_string(message.text)
        query = search_input.query
    except ValueError as e:
        await message.answer(f"❌ {str(e)}")
        return
        
    clinics = await search_clinics(session, query, limit=10)
    
    if not clinics:
        await message.answer("❌ Клиники не найдены. Попробуйте другой запрос или добавьте клинику через администратора.")
        return

    # Display results
    rows = []
    for clinic in clinics:
        label = f"{clinic.name} ({clinic.doctor_name})"
        rows.append([
            InlineKeyboardButton(
                text=label,
                callback_data=f"select_clinic:{clinic.id}"
            )
        ])
    
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_search")])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    
    await message.answer(f"Найдено {len(clinics)} вариантов:", reply_markup=kb)
    await state.set_state(ManagerOrderState.selecting_clinic)

@router.callback_query(F.data == "cancel_search")
async def cancel_search(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    # Go back to cart view
    # Access cart view using existing logic
    # We need to manually call view_cart or reconstruct it
    await callback.message.answer("Поиск отменен. Вернитесь в корзину через меню.")
    await cmd_menu(callback.message, state) # Fallback to menu

@router.callback_query(F.data.startswith("select_clinic:"))
async def select_clinic(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    clinic_id = int(callback.data.split(":")[1])
    logger.info("catalog user=%s select_clinic clinic_id=%s", callback.from_user.id, clinic_id)
    
    # Store selected clinic
    await state.update_data(selected_clinic_id=clinic_id)
    
    # Fetch clinic name for confirmation
    result = await session.execute(select(Clinic).where(Clinic.id == clinic_id))
    clinic = result.scalar_one()
    clinic_name = clinic.name
        
    await callback.message.edit_text(f"✅ Выбрана клиника: *{clinic_name}*.", parse_mode="Markdown")
    
    # Trigger finalization
    await finalize_order(callback, state, session)


async def finalize_order(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    """Создание заказа через OrderService с транзакцией."""
    from services.order_service import OrderService
    from database.models import DeliveryType
    
    data = await state.get_data()
    cart = data.get('cart', [])
    clinic_id = data.get('selected_clinic_id')
    is_urgent = data.get('is_urgent', False)
    delivery_type_str = data.get('delivery_type', "courier")
    
    items_summary = [(i["sku"], i["quantity"]) for i in cart]
    logger.info(
        "catalog user=%s finalize_order clinic_id=%s cart_len=%s items=%s urgent=%s delivery=%s",
        callback.from_user.id, clinic_id, len(cart), items_summary, is_urgent, delivery_type_str
    )
    
    manager_user = await get_user_by_telegram_id(session, callback.from_user.id, use_cache=True)
    if not manager_user:
        logger.warning("catalog user=%s finalize_order manager_not_found", callback.from_user.id)
        await callback.answer("❌ Ошибка: пользователь не найден", show_alert=True)
        return
    
    if not cart:
        await callback.answer("❌ Корзина пуста", show_alert=True)
        return
    
    if not clinic_id:
        await callback.answer("❌ Клиника не выбрана", show_alert=True)
        return
    
    # Создаем заказ через сервис (с транзакцией)
    delivery_type = DeliveryType(delivery_type_str)
    order, error = await OrderService.create_order(
        session=session,
        manager_id=manager_user.id,
        clinic_id=clinic_id,
        cart=cart,
        is_urgent=is_urgent,
        delivery_type=delivery_type
    )
    
    if error:
        logger.warning(
            "catalog user=%s finalize_order failed: %s",
            callback.from_user.id, error
        )
        await callback.answer(f"❌ {error}", show_alert=True)
        return
    
    if not order:
        await callback.answer("❌ Ошибка создания заказа", show_alert=True)
        return
    
    logger.info(
        "catalog user=%s finalize_order success order_id=%s clinic_id=%s items=%s",
        callback.from_user.id, order.id, clinic_id, items_summary
    )
    await callback.message.answer(f"✅ Заказ #{order.id} успешно создан и отправлен на склад!")
    await state.clear()


# --- Order Management ---

ORDERS_PER_PAGE = 15


async def _load_manager_orders_page(session: AsyncSession, manager_user_id: int, page: int):
    """Загружает страницу заказов менеджера с пагинацией."""
    from sqlalchemy.orm import selectinload
    from sqlalchemy import func
    # Общее количество
    count_stmt = (
        select(func.count(Order.id))
        .where(Order.manager_id == manager_user_id)
    )
    total_result = await session.execute(count_stmt)
    total_count = total_result.scalar() or 0
    # Страница заказов
    offset = page * ORDERS_PER_PAGE
    stmt = (
        select(Order)
        .options(selectinload(Order.clinic), selectinload(Order.items))
        .where(Order.manager_id == manager_user_id)
        .order_by(Order.created_at.desc())
        .limit(ORDERS_PER_PAGE)
        .offset(offset)
    )
    result = await session.execute(stmt)
    orders = result.scalars().all()
    return orders, total_count


@router.callback_query(F.data == "manager:orders")
@router.callback_query(F.data.startswith("manager:orders:page:"))
async def manager_menu_orders(callback: types.CallbackQuery, session: AsyncSession):
    """Показать заказы менеджера в виде кнопок с пагинацией."""
    if not await is_manager(callback.from_user.id, session):
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    
    manager_user = await get_user_by_telegram_id(session, callback.from_user.id, use_cache=True)
    if not manager_user:
        await callback.answer("Ошибка: пользователь не найден", show_alert=True)
        return
    
    page = 0
    if callback.data and callback.data.startswith("manager:orders:page:"):
        try:
            page = int(callback.data.split(":")[-1])
        except (ValueError, IndexError):
            page = 0
    
    orders, total_count = await _load_manager_orders_page(session, manager_user.id, page)
    
    if not orders:
        await callback.message.edit_text(
            "📋 *Мои заказы*\n\nУ вас пока нет заказов.\n\n"
            "🟡 собирается на складе | 🔵 доставляется | 🟢 доставлен | 🔴 отменён",
            parse_mode="Markdown",
            reply_markup=get_manager_menu_kb()
        )
        await callback.answer()
        return
    
    total_pages = max(1, (total_count + ORDERS_PER_PAGE - 1) // ORDERS_PER_PAGE)
    text = (
        f"📋 *Мои заказы* (страница {page + 1}/{total_pages})\n\n"
        f"Всего заказов: {total_count}\n\n"
        "🟡 собирается | 🔵 доставка | 🟢 доставлен | 🔴 отменён"
    )
    kb = make_manager_orders_list_kb(orders, page=page, per_page=ORDERS_PER_PAGE, total_count=total_count)
    try:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            raise
    await callback.answer()


@router.callback_query(F.data.startswith("manager:order:"))
async def manager_order_detail(callback: types.CallbackQuery, session: AsyncSession):
    """Показать полные данные заказа при нажатии на кнопку."""
    if not await is_manager(callback.from_user.id, session):
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    
    try:
        order_id = int(callback.data.split(":")[-1])
    except (ValueError, IndexError):
        await callback.answer("Ошибка", show_alert=True)
        return
    
    from sqlalchemy.orm import selectinload
    stmt = (
        select(Order)
        .options(selectinload(Order.clinic), selectinload(Order.items))
        .where(Order.id == order_id)
    )
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()
    
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    
    manager_user = await get_user_by_telegram_id(session, callback.from_user.id, use_cache=True)
    if not manager_user or order.manager_id != manager_user.id:
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    
    status_names = {
        OrderStatus.NEW: "🆕 Новый",
        OrderStatus.ASSEMBLY: "🔧 В сборке",
        OrderStatus.READY_FOR_PICKUP: "📦 Готов к выдаче",
        OrderStatus.DELIVERING: "🚚 В доставке",
        OrderStatus.DELIVERED: "✅ Доставлен",
        OrderStatus.CANCELED: "❌ Отменён",
    }
    status_name = status_names.get(order.status, order.status.value)
    created_date = order.created_at.strftime("%d.%m.%Y %H:%M") if order.created_at else "—"
    assembled_date = order.assembled_at.strftime("%d.%m.%Y %H:%M") if order.assembled_at else "—"
    delivered_date = order.delivered_at.strftime("%d.%m.%Y %H:%M") if order.delivered_at else "—"
    
    text = (
        f"📦 *Заказ #{order.id}*\n\n"
        f"*Клиника:* {order.clinic.name if order.clinic else '—'}\n"
        f"*Врач:* {order.clinic.doctor_name if order.clinic else '—'}\n"
        f"*Статус:* {status_name}\n"
        f"*Создан:* {created_date}\n"
        f"*Собран:* {assembled_date}\n"
        f"*Доставлен:* {delivered_date}\n"
        f"*Срочный:* {'Да' if order.is_urgent else 'Нет'}\n"
        f"*Доставка:* {order.delivery_type.value if order.delivery_type else '—'}\n"
    )
    if order.taxi_link:
        text += f"*Ссылка такси:* {order.taxi_link}\n"
    
    text += "\n*Товары:*\n"
    for item in order.items or []:
        text += f"• {item.item_name} — {item.quantity} шт\n"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅ К списку заказов", callback_data="manager:orders")]
    ])
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
    await callback.answer()
