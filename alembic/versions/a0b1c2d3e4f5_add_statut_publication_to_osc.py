"""add statut_publication to osc

Revision ID: a0b1c2d3e4f5
Revises: e3f4a5b6c7d8
Create Date: 2026-08-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a0b1c2d3e4f5"
down_revision: Union[str, None] = "e3f4a5b6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("osc", sa.Column("statut_publication", sa.String(20), nullable=False, server_default="publie"))


def downgrade() -> None:
    op.drop_column("osc", "statut_publication")
