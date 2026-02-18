"""
Сервис для автоматической загрузки каталога из Excel при старте бота.
"""
import logging
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def load_catalog_automatically(excel_filename: Optional[str] = None) -> bool:
    """
    Автоматически загружает каталог из Excel файла и обновляет catalog_data.py.
    
    Args:
        excel_filename: Имя файла Excel. Если None, ищет автоматически.
    
    Returns:
        True если загрузка успешна, False в противном случае.
    """
    try:
        # Импортируем функцию загрузки
        from load_catalog_from_excel import load_catalog_from_excel, generate_catalog_file, print_statistics
        
        # Определяем файл для загрузки
        if excel_filename:
            file_path = Path(excel_filename)
        else:
            # Автоматически ищем файл из конфигурации
            from config import config
            possible_files = config.CATALOG_POSSIBLE_FILES_LIST
            
            file_path = None
            for filename in possible_files:
                path = Path(filename)
                if path.exists():
                    file_path = path
                    logger.info("Found catalog file: %s", filename)
                    break
            
            if not file_path:
                logger.warning("No catalog Excel file found. Using existing catalog_data.py")
                return False
        
        if not file_path or not file_path.exists():
            logger.warning("Catalog file not found: %s. Using existing catalog_data.py", excel_filename or 'auto')
            return False
        
        logger.info("Loading catalog from: %s", file_path)
        
        # Загружаем каталог
        result = load_catalog_from_excel(str(file_path))
        
        if not result:
            logger.error("Failed to load catalog from Excel. Using existing catalog_data.py")
            return False
        
        # Распаковываем результат: (catalog, visibility)
        catalog, visibility = result
        
        if not catalog:
            logger.error("Failed to load catalog from Excel. Using existing catalog_data.py")
            return False
        
        # Генерируем catalog_data.py
        generate_catalog_file(catalog, visibility)
        
        # Перезагружаем модуль catalog_data, если он уже был импортирован
        if 'catalog_data' in sys.modules:
            import importlib
            import catalog_data
            importlib.reload(catalog_data)
            logger.info("Reloaded catalog_data module")
        
        # Инициализируем остатки из каталога (USE_CATALOG_STOCK)
        try:
            from config import config
            if getattr(config, "USE_CATALOG_STOCK", False):
                from services.catalog_stock import init_from_catalog
                init_from_catalog()
                logger.info("Catalog stock initialized from catalog")
        except Exception as e:
            logger.debug("Catalog stock init skipped: %s", e)
        
        # Выводим статистику
        print_statistics(catalog)
        
        logger.info("✅ Catalog loaded and synchronized successfully")
        return True
        
    except ImportError as e:
        logger.error("Failed to import catalog loader: %s", e)
        logger.warning("Using existing catalog_data.py")
        return False
    except Exception as e:
        logger.error("Error loading catalog: %s", e, exc_info=True)
        logger.warning("Using existing catalog_data.py")
        return False
