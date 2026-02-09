"""
Миграция каталога для полноценной работы бота.

Выполняет:
1. Загрузку каталога из Excel (catalog_template.xlsx, Megagenbot.xlsx или catalog.xlsx)
2. Генерацию catalog_data.py и catalog.json
3. Инициализацию остатков catalog_stock.json (для USE_CATALOG_STOCK)

Использование:
    python migrate_catalog.py [filename.xlsx]

Без аргументов ищет файл автоматически.
"""
import sys
import logging
from pathlib import Path

# load_catalog_from_excel настраивает UTF-8 для stdout при импорте
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def find_excel_file(specified: str | None = None) -> Path | None:
    """Находит Excel файл каталога."""
    candidates = [
        specified,
        "catalog_template.xlsx",
        "Megagenbot.xlsx",
        "catalog.xlsx",
    ]
    for name in candidates:
        if not name:
            continue
        path = Path(name)
        if path.exists():
            return path
    return None


def migrate_catalog(excel_path: Path | None = None) -> bool:
    """
    Выполняет миграцию каталога: Excel -> catalog_data.py, catalog.json, catalog_stock.json.
    
    Returns:
        True при успехе, False при ошибке.
    """
    if not excel_path:
        excel_path = find_excel_file()
    
    if not excel_path or not excel_path.exists():
        logger.error("❌ Файл каталога не найден.")
        logger.info("Ожидаемые файлы: catalog_template.xlsx, Megagenbot.xlsx, catalog.xlsx")
        logger.info("Или укажите путь: python migrate_catalog.py путь/к/файлу.xlsx")
        return False

    logger.info("=" * 60)
    logger.info("Миграция каталога")
    logger.info("=" * 60)
    logger.info("Файл: %s", excel_path)

    try:
        from load_catalog_from_excel import (
            load_catalog_from_excel,
            generate_catalog_file,
            print_statistics,
        )
    except ImportError as e:
        logger.error("❌ Не удалось импортировать load_catalog_from_excel: %s", e)
        return False

    result = load_catalog_from_excel(str(excel_path))
    if not result:
        logger.error("❌ Ошибка загрузки каталога из Excel.")
        return False

    catalog, visibility = result
    if not catalog:
        logger.error("❌ Каталог пуст.")
        return False

    # 1. Генерируем catalog_data.py
    generate_catalog_file(catalog, visibility)
    logger.info("✅ catalog_data.py")

    # 2. Сохраняем catalog.json
    import json
    with open("catalog.json", "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
    logger.info("✅ catalog.json")

    # 3. Инициализируем остатки (catalog_stock.json)
    try:
        from services.catalog_stock import init_from_catalog
        init_from_catalog()
        logger.info("✅ catalog_stock.json (остатки)")
    except Exception as e:
        logger.warning("⚠️ catalog_stock не инициализирован: %s", e)

    # Статистика
    print_statistics(catalog)

    logger.info("")
    logger.info("=" * 60)
    logger.info("✅ Миграция каталога завершена успешно.")
    logger.info("Перезапустите бота для применения изменений.")
    logger.info("=" * 60)
    return True


def main():
    specified = sys.argv[1] if len(sys.argv) > 1 else None
    success = migrate_catalog(Path(specified) if specified else None)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
