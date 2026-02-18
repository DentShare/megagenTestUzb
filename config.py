"""
Конфигурация приложения с валидацией через Pydantic.
"""
import os
from typing import List, Optional
from pathlib import Path
from pydantic import Field, field_validator, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()


class Config(BaseSettings):
    """Конфигурация приложения с валидацией."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Database
    DB_DIALECT: str = Field(default="sqlite", description="Тип БД: postgres или sqlite")
    DB_POOL_SIZE: int = Field(default=10, description="Размер пула соединений PostgreSQL (для 30-40 сотрудников достаточно 10)")
    DB_MAX_OVERFLOW: int = Field(default=10, description="Доп. соединений поверх pool_size")
    DB_USER: str = Field(default="postgres", description="Пользователь БД")
    DB_PASS: str = Field(default="postgres", description="Пароль БД")
    DB_HOST: str = Field(default="localhost", description="Хост БД")
    DB_PORT: str = Field(default="5432", description="Порт БД")
    DB_NAME: str = Field(default="megagen_bot", description="Имя БД")
    SQLITE_PATH: str = Field(default="megagen_bot.sqlite3", description="Путь к SQLite файлу")
    # Railway и др. платформы передают один DATABASE_URL — если задан, используем его
    DATABASE_URL_OVERRIDE: Optional[str] = Field(default=None, description="URL БД", validation_alias="DATABASE_URL")

    @field_validator("DB_DIALECT")
    @classmethod
    def validate_db_dialect(cls, v: str) -> str:
        """Валидация типа БД."""
        v = v.lower()
        if v not in ("postgres", "postgresql", "sqlite", "sqlite3"):
            raise ValueError(f"Неподдерживаемый тип БД: {v}")
        return v
    
    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        """URL подключения к БД. Если задан DATABASE_URL (Railway и др.) — используем его."""
        raw = self.DATABASE_URL_OVERRIDE
        if raw:
            raw = raw.strip()
            # PostgreSQL от Railway: postgresql://... → для asyncpg нужен postgresql+asyncpg://
            if raw.startswith("postgresql://") and "+asyncpg" not in raw:
                return raw.replace("postgresql://", "postgresql+asyncpg://", 1)
            return raw
        if self.DB_DIALECT in ("sqlite", "sqlite3"):
            base_dir = Path(__file__).resolve().parent
            db_path = Path(self.SQLITE_PATH)
            if not db_path.is_absolute():
                db_path = base_dir / db_path
            return f"sqlite+aiosqlite:///{db_path.resolve().as_posix()}"
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # Bot
    BOT_TOKEN: str = Field(default="", description="Токен Telegram бота")
    ADMIN_IDS: str = Field(default="", description="ID администраторов через запятую")
    
    @field_validator("BOT_TOKEN")
    @classmethod
    def validate_bot_token(cls, v: str) -> str:
        """Валидация токена бота."""
        if not v:
            raise ValueError("BOT_TOKEN обязателен для работы бота")
        return v
    
    @computed_field
    @property
    def ADMIN_IDS_LIST(self) -> List[int]:
        """Список ID администраторов."""
        if not self.ADMIN_IDS:
            return []
        return [int(id_str.strip()) for id_str in self.ADMIN_IDS.split(",") if id_str.strip()]
    
    # Google Sheets
    GOOGLE_SERVICE_ACCOUNT_JSON: str = Field(default="", description="Путь к JSON файлу или JSON строка")
    GOOGLE_SHEETS_FOLDER_ID: str = Field(default="", description="ID папки для новых таблиц")
    
    # Redis
    REDIS_HOST: str = Field(default="localhost", description="Хост Redis")
    REDIS_PORT: int = Field(default=6379, description="Порт Redis")
    REDIS_DB: int = Field(default=0, description="Номер БД Redis")
    REDIS_PASSWORD: Optional[str] = Field(default=None, description="Пароль Redis")
    REDIS_CACHE_TTL: int = Field(default=300, description="TTL кеша в секундах")
    REDIS_RATE_LIMIT_TTL: int = Field(default=60, description="TTL rate limit в секундах")
    
    # 1C Integration
    ONE_C_MODE: str = Field(default="test", description="Режим работы 1С: test или real")
    ONE_C_API_URL: str = Field(default="", description="URL API 1С")
    ONE_C_USERNAME: str = Field(default="", description="Имя пользователя 1С")
    ONE_C_PASSWORD: str = Field(default="", description="Пароль 1С")
    ONE_C_TIMEOUT: int = Field(default=30, description="Таймаут запросов к 1С в секундах")
    ONE_C_RETRY_ATTEMPTS: int = Field(default=3, description="Количество попыток при ошибке")
    
    @field_validator("ONE_C_MODE")
    @classmethod
    def validate_one_c_mode(cls, v: str) -> str:
        """Валидация режима 1С."""
        v = v.lower()
        if v not in ("test", "real"):
            raise ValueError(f"Неподдерживаемый режим 1С: {v}")
        return v
    
    @computed_field
    @property
    def ONE_C_IS_TEST_MODE(self) -> bool:
        """Проверка, используется ли тестовый режим 1С."""
        return self.ONE_C_MODE == "test"
    
    # Catalog
    CATALOG_AUTO_SYNC: bool = Field(default=True, description="Автосинхронизация каталога при старте")
    CATALOG_EXCEL_FILE: str = Field(default="", description="Путь к Excel файлу каталога")
    CATALOG_POSSIBLE_FILES: str = Field(
        default="catalog_template.xlsx,Megagenbot.xlsx,catalog.xlsx",
        description="Возможные имена файлов каталога через запятую"
    )
    USE_CATALOG_STOCK: bool = Field(default=True, description="Использовать остатки из каталога")
    
    @computed_field
    @property
    def CATALOG_POSSIBLE_FILES_LIST(self) -> List[str]:
        """Список возможных файлов каталога."""
        return [f.strip() for f in self.CATALOG_POSSIBLE_FILES.split(",") if f.strip()]
    
    # Pagination (для 30-40 сотрудников)
    USERS_PER_PAGE: int = Field(default=40, description="Количество пользователей на странице")
    ORDERS_PER_PAGE: int = Field(default=25, description="Количество заказов на странице")
    
    # Keyboard Layout Settings (количество кнопок в строке)
    CATEGORY_BUTTONS_PER_ROW: int = Field(default=1, description="Кнопок категорий в строке (1=вертикально, 2=по 2 в строке)")
    LINE_BUTTONS_PER_ROW: int = Field(default=1, description="Кнопок линеек в строке")
    DIAMETER_BUTTONS_PER_ROW: int = Field(default=2, description="Кнопок диаметров в строке")
    GUM_HEIGHT_BUTTONS_PER_ROW: int = Field(default=2, description="Кнопок высоты десны в строке")
    ABUTMENT_HEIGHT_BUTTONS_PER_ROW: int = Field(default=2, description="Кнопок высоты абатмента в строке")
    ITEM_BUTTONS_PER_ROW: int = Field(default=1, description="Кнопок товаров в строке")
    NO_SIZE_BUTTONS_PER_ROW: int = Field(default=1, description="Кнопок товаров без размеров в строке")
    
    # Priority Settings (приоритетные категории и линейки - показываются сразу, остальные в "Дополнительно")
    PRIORITY_CATEGORIES: str = Field(
        default="Импланты,Протетика",
        description="Приоритетные категории через запятую (показываются сразу, остальные в 'Дополнительно')"
    )
    PRIORITY_LINES: str = Field(
        default="AnyOne,AO Onestage",
        description="Приоритетные линейки через запятую (для категории 'Импланты', остальные в 'Дополнительно')"
    )
    PRIORITY_PROSTHETICS_PRODUCTS: str = Field(
        default="",
        description="Приоритетные товары (виды) для категории 'Протетика' через запятую (остальные в 'Дополнительно')"
    )
    PRIORITY_LABORATORY_PRODUCTS: str = Field(
        default="",
        description="Приоритетные товары (виды) для категории 'Лаборатория' через запятую (остальные в 'Дополнительно')"
    )
    PRIORITY_SETS_PRODUCTS: str = Field(
        default="",
        description="Приоритетные товары (виды) для категории 'Наборы' через запятую (остальные в 'Дополнительно')"
    )
    
    @computed_field
    @property
    def PRIORITY_CATEGORIES_LIST(self) -> List[str]:
        """Список приоритетных категорий."""
        return [c.strip() for c in self.PRIORITY_CATEGORIES.split(",") if c.strip()]
    
    @computed_field
    @property
    def PRIORITY_LINES_LIST(self) -> List[str]:
        """Список приоритетных линеек."""
        return [l.strip() for l in self.PRIORITY_LINES.split(",") if l.strip()]
    
    @computed_field
    @property
    def PRIORITY_PROSTHETICS_PRODUCTS_LIST(self) -> List[str]:
        """Список приоритетных товаров для Протетики."""
        return [p.strip() for p in self.PRIORITY_PROSTHETICS_PRODUCTS.split(",") if p.strip()]
    
    @computed_field
    @property
    def PRIORITY_LABORATORY_PRODUCTS_LIST(self) -> List[str]:
        """Список приоритетных товаров для Лаборатории."""
        return [p.strip() for p in self.PRIORITY_LABORATORY_PRODUCTS.split(",") if p.strip()]
    
    @computed_field
    @property
    def PRIORITY_SETS_PRODUCTS_LIST(self) -> List[str]:
        """Список приоритетных товаров для Наборов."""
        return [p.strip() for p in self.PRIORITY_SETS_PRODUCTS.split(",") if p.strip()]
    
    # Rate Limiting (для 30-40 сотрудников; лимит на одного пользователя за период)
    RATE_LIMIT_MESSAGE_MAX: int = Field(default=60, description="Максимум сообщений за период (на пользователя)")
    RATE_LIMIT_CALLBACK_MAX: int = Field(default=200, description="Максимум callback за период (на пользователя)")
    RATE_LIMIT_PERIOD: float = Field(default=60.0, description="Период rate limit в секундах")
    
    # Printer (Xprinter)
    PRINTER_ENABLED: bool = Field(default=False, description="Включить автоматическую печать этикеток")
    PRINTER_TYPE: str = Field(default="usb", description="Тип подключения: usb, network, serial")
    PRINTER_ADDRESS: str = Field(default="", description="Адрес принтера (USB путь, IP адрес или COM порт)")
    PRINTER_NETWORK_PORT: int = Field(default=9100, description="Порт для сетевого принтера")
    PRINTER_SERIAL_BAUDRATE: int = Field(default=9600, description="Скорость для serial принтера")
    PRINTER_WIDTH_MM: int = Field(default=58, description="Ширина ленты в мм (58 или 80)")
    
    @field_validator("PRINTER_TYPE")
    @classmethod
    def validate_printer_type(cls, v: str) -> str:
        """Валидация типа принтера."""
        v = v.lower()
        if v not in ("usb", "network", "serial"):
            raise ValueError(f"Неподдерживаемый тип принтера: {v}. Допустимые: usb, network, serial")
        return v
    
    @field_validator("PRINTER_WIDTH_MM")
    @classmethod
    def validate_printer_width(cls, v: int) -> int:
        """Валидация ширины принтера."""
        if v not in (58, 80):
            raise ValueError(f"Неподдерживаемая ширина принтера: {v}. Допустимые: 58, 80")
        return v
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Уровень логирования")
    DEBUG: bool = Field(default=False, description="Режим отладки")
    
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Валидация уровня логирования."""
        v = v.upper()
        valid_levels = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        if v not in valid_levels:
            raise ValueError(f"Неподдерживаемый уровень логирования: {v}. Допустимые: {valid_levels}")
        return v


# Создаем экземпляр конфигурации с валидацией
try:
    config = Config()
except Exception as e:
    import sys
    print(f"❌ Ошибка загрузки конфигурации: {e}", file=sys.stderr)
    sys.exit(1)
