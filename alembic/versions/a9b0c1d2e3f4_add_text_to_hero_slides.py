"""add text to hero slides

Revision ID: a9b0c1d2e3f4
Revises: f6a7b8c9d0e1
Create Date: 2026-06-26 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a9b0c1d2e3f4"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("hero_slide", sa.Column("title", sa.String(length=200), nullable=True))
    op.add_column("hero_slide", sa.Column("description", sa.String(length=1000), nullable=True))


def downgrade() -> None:
    op.drop_column("hero_slide", "description")
    op.drop_column("hero_slide", "title")
