import random
import asyncio
import hashlib
from typing import Dict
from functools import wraps
from config import config


def retry(max_attempts: int = 3, delay: float = 1.0):
    """Декоратор для повторных попыток при ошибках."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(delay * (attempt + 1))  # Exponential backoff
                    else:
                        raise
            if last_exception:
                raise last_exception
        return wrapper
    return decorator


def _get_test_stock(product_line: str, diameter: float) -> Dict[float, int]:
    """
    Тестовая функция для получения остатков товара.
    Возвращает предсказуемые данные на основе product_line и diameter.
    Используется для тестирования без реального подключения к 1С.
    """
    # Стандартный набор длин
    lengths = [7.0, 8.5, 10.0, 11.5, 13.0, 15.0]
    
    # Создаем детерминированный хеш на основе product_line и diameter
    # для получения предсказуемых, но разнообразных данных
    hash_input = f"{product_line}_{diameter}".encode('utf-8')
    hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)
    
    stock = {}
    for idx, length in enumerate(lengths):
        # Используем хеш для генерации предсказуемых значений
        # Это позволяет получать одинаковые данные для одних и тех же параметров
        seed = (hash_value + idx * 1000) % 1000
        
        # Некоторые позиции будут с нулевым остатком (для тестирования)
        if seed % 5 == 0:
            qty = 0
        else:
            # Остатки от 5 до 100 для реалистичности
            qty = (seed % 95) + 5
        
        stock[length] = qty
    
    return stock


async def _get_real_stock(product_line: str, diameter: float) -> Dict[float, int]:
    """
    Реальная функция для получения остатков из 1С.
    TODO: Реализовать реальное подключение к API 1С.
    
    Для синхронизации с 1C используйте артикулы из каталога (CATALOG).
    Артикулы хранятся в структуре: CATALOG[category][line][diameter][length]['sku']
    """
    # Здесь будет реализация реального подключения к 1С
    # Пример структуры с использованием артикулов:
    # import aiohttp
    # from catalog_data import CATALOG
    # 
    # # Получаем артикулы для данной линейки и диаметра
    # skus = []
    # for category in CATALOG.values():
    #     if product_line in category:
    #         line_data = category[product_line]
    #         if diameter in line_data:
    #             for length, product_info in line_data[diameter].items():
    #                 skus.append({
    #                     'sku': product_info['sku'],
    #                     'length': length
    #                 })
    # 
    # # Запрос к 1C API по артикулам
    # async with aiohttp.ClientSession() as session:
    #     async with session.post(
    #         f"{config.ONE_C_API_URL}/stock/batch",
    #         json={"skus": [item['sku'] for item in skus]},
    #         auth=aiohttp.BasicAuth(config.ONE_C_USERNAME, config.ONE_C_PASSWORD)
    #     ) as response:
    #         data = await response.json()
    #         # Преобразуем ответ в формат {length: quantity}
    #         stock_map = {item['sku']: item['quantity'] for item in data}
    #         return {
    #             item['length']: stock_map.get(item['sku'], 0)
    #             for item in skus
    #         }
    
    raise NotImplementedError(
        "Реальная интеграция с 1С не реализована. "
        "Используйте тестовый режим (ONE_C_MODE=test) или реализуйте подключение к API 1С. "
        "Артикулы для синхронизации доступны в CATALOG через поле 'sku'."
    )


@retry(max_attempts=3, delay=1.0)
async def get_stock(product_line: str, diameter: float, diameter_body: float | None = None) -> Dict[float, int]:
    """
    Получение остатков товара из 1С или из каталога (Excel).
    diameter_body: для имплантов "4.5 [3.8]" — диаметр тела, отдельный продукт.
    
    При USE_CATALOG_STOCK=true: остатки из таблицы, вычитание при заказе.
    Иначе: тестовый режим (mock) или 1С.
    
    Returns:
        Словарь: ключ — длина/высота десны (float), значение — количество (int)
    """
    if getattr(config, "USE_CATALOG_STOCK", False):
        from services.catalog_stock import get_stock as _catalog_stock
        return _catalog_stock(product_line, diameter, diameter_body)
    if config.ONE_C_IS_TEST_MODE:
        return _get_test_stock(product_line, diameter)
    return await _get_real_stock(product_line, diameter)


def get_sku(product_line: str, diameter: float, length: float) -> str:
    """
    Генерация SKU (артикула) товара.
    
    Args:
        product_line: Название линейки продукции
        diameter: Диаметр товара
        length: Длина товара
        
    Returns:
        SKU в формате: ПРЕФИКС-ДИАМЕТР-ДЛИНА
    """
    return f"{product_line[:3].upper()}-{diameter}-{length}".replace(".", "")
