"""
Карта продукции — настраиваемое меню с кнопками и файлами.
Структура задаётся в product_map_config.json.
Файлы (PDF, PNG) кладите в папку product_map_files/.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).resolve().parent / "product_map_config.json"
FILES_DIR = Path(__file__).resolve().parent / "product_map_files"

# Callback prefix для карты продукции (до 64 байт)
PREFIX = "pmap:"


def _collect_all_files(config: dict, prefix: List[str]) -> List[Tuple[List[str], str]]:
    """Рекурсивно собирает все файлы: [(path_parts, filename), ...] в детерминированном порядке."""
    result = []
    for key in sorted(config.keys()):
        if key.startswith("_"):
            continue
        node = config[key]
        if not isinstance(node, dict):
            continue
        if "file" in node:
            result.append((prefix + [key], node["file"]))
        elif "children" in node:
            result.extend(_collect_all_files(node["children"], prefix + [key]))
    return result


def get_file_path_by_index(index: int) -> Optional[Path]:
    """По индексу (порядок обхода конфига) возвращает путь к файлу."""
    config = _load_config()
    if not config:
        return None
    files = _collect_all_files(config, [])
    if index < 0 or index >= len(files):
        return None
    _, filename = files[index]
    return _get_file_path(filename)


def _load_config() -> Dict[str, Any]:
    """Загружает конфиг карты продукции."""
    if not CONFIG_PATH.exists():
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Убираем служебные ключи
        return {k: v for k, v in data.items() if not k.startswith("_")}
    except Exception as e:
        logger.warning("product_map: failed to load config: %s", e)
        return {}


def _get_file_path(filename: str) -> Optional[Path]:
    """Возвращает путь к файлу в product_map_files/."""
    if not filename or ".." in filename:
        return None
    path = FILES_DIR / filename
    if path.exists() and path.is_file():
        return path
    return None


def get_product_map_keyboard(path: Optional[str] = None) -> Tuple[InlineKeyboardMarkup, Optional[str]]:
    """
    Строит клавиатуру карты продукции.
    
    Args:
        path: Путь в меню через "|", например "Импланты|AnyOne" или None для корня.
    
    Returns:
        (keyboard, message) — клавиатура и текст сообщения (None = использовать дефолт).
    """
    config = _load_config()
    if not config:
        return InlineKeyboardMarkup(inline_keyboard=[]), "Карта продукции пуста. Добавьте пункты в product_map_config.json."
    
    # Собираем все файлы для маппинга path -> index (при длинных путях >64 байт)
    all_files = _collect_all_files(config, [])
    path_to_index = {"|".join(parts): i for i, (parts, _) in enumerate(all_files)}
    
    # Определяем текущий уровень
    if path:
        parts = [p.strip() for p in path.split("|") if p.strip()]
        current = config
        for p in parts:
            if isinstance(current, dict) and p in current:
                node = current[p]
                if isinstance(node, dict) and "children" in node:
                    current = node["children"]
                else:
                    current = node
            else:
                current = {}
                break
    else:
        parts = []
        current = config
    
    rows = []
    
    # Кнопки текущего уровня
    if isinstance(current, dict):
        for key in sorted(current.keys()):
            if key.startswith("_"):
                continue
            value = current[key]
            if isinstance(value, dict):
                if "children" in value:
                    # Подменю
                    cb = f"{PREFIX}{path + '|' + key if path else key}"
                    if len(cb.encode("utf-8")) > 64:
                        cb = f"{PREFIX}{len(parts)}:{key}"  # fallback
                    rows.append([InlineKeyboardButton(text=f"📁 {key}", callback_data=cb)])
                elif "file" in value:
                    # Файл: при длинном пути используем индекс
                    path_str = f"{path + '|' + key if path else key}"
                    cb = f"{PREFIX}file:{path_str}"
                    if len(cb.encode("utf-8")) > 64:
                        idx = path_to_index.get(path_str)
                        if idx is not None:
                            cb = f"{PREFIX}file:{idx}"
                        else:
                            cb = f"{PREFIX}file:{path_str[:20]}"  # fallback
                    rows.append([InlineKeyboardButton(text=f"📄 {key}", callback_data=cb)])
    
    # Кнопка "Назад" если не в корне
    if parts:
        parent_path = "|".join(parts[:-1]) if len(parts) > 1 else None
        back_cb = f"{PREFIX}back:{parent_path}" if parent_path else f"{PREFIX}root"
        rows.append([InlineKeyboardButton(text="◀ Назад", callback_data=back_cb)])
    
    # Кнопка в главное меню
    rows.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="manager:main")])
    
    title = parts[-1] if parts else "Карта продукции"
    msg = f"📂 {title}\n\nВыберите раздел или файл:"
    
    return InlineKeyboardMarkup(inline_keyboard=rows), msg


def resolve_file_path(path_str: str) -> Optional[Path]:
    """
    По пути в меню (например "Импланты|AnyOne|Инструкция") находит файл.
    """
    config = _load_config()
    if not path_str or not config:
        return None
    
    parts = [p.strip() for p in path_str.split("|") if p.strip()]
    if not parts:
        return None
    
    current = config
    for i, p in enumerate(parts):
        if p not in current:
            return None
        node = current[p]
        if i == len(parts) - 1:
            if isinstance(node, dict) and "file" in node:
                return _get_file_path(node["file"])
            return None
        if isinstance(node, dict) and "children" in node:
            current = node["children"]
        else:
            return None
    
    return None
