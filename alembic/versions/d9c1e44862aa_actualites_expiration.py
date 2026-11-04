"""actualités : désactivation automatique et archives

Retours PdoC (Frontend/Temporalité des actualités) : « mettre un délai de
désactivation automatique d'une actualité et les mettre en archive sous le
profil de l'OSC ». news.date_expiration : après cette date l'actualité quitte
les listes publiques et reste visible dans les archives de l'OSC.

Revision ID: d9c1e44862aa
Revises: c9c625bef9fa
Create Date: 2026-11-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d9c1e44862aa"
down_revision: Union[str, None] = "c9c625bef9fa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("news", sa.Column("date_expiration", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("news", "date_expiration")
