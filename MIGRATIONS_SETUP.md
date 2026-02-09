# Настройка миграций БД (Alembic)

## Установка

```bash
pip install alembic
```

## Инициализация

```bash
alembic init alembic
```

## Конфигурация

Отредактируйте `alembic/env.py`:

```python
from config import config
from database.models import Base

# Используем DATABASE_URL из конфигурации
url = config.DATABASE_URL.replace("+aiosqlite", "").replace("+asyncpg", "")

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    connectable = engine_from_config(
        {"sqlalchemy.url": url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    # ... остальной код
```

## Создание миграций

```bash
# Автоматическое создание миграции на основе изменений моделей
alembic revision --autogenerate -m "Описание изменений"

# Применение миграций
alembic upgrade head

# Откат миграции
alembic downgrade -1
```

## Важно

- Миграции нужно создавать при каждом изменении моделей в `database/models.py`
- Всегда проверяйте сгенерированные миграции перед применением
- В продакшене применяйте миграции с осторожностью, делайте бэкапы

