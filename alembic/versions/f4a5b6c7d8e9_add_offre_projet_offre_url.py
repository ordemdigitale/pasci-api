"""add offer link to project offers

Revision ID: f4a5b6c7d8e9
Revises: f3a4b5c6d7e8
Create Date: 2026-06-12 12:45:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4a5b6c7d8e9"
down_revision: Union[str, Sequence[str], None] = "f3a4b5c6d7e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("offreprojet", schema=None) as batch_op:
        batch_op.add_column(sa.Column("offre_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("offreprojet", schema=None) as batch_op:
        batch_op.drop_column("offre_url")
