"""initial — baseline для существующей БД.

Revision ID: 1b89f463a6df
Revises:
Create Date: 2026-02-18 22:46:11.312613

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1b89f463a6df'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Baseline: таблицы уже созданы через create_all().
    # Будущие изменения схемы добавлять новыми миграциями.
    pass


def downgrade() -> None:
    # Откат baseline не поддерживается — пересоздайте БД вручную.
    pass
