"""osc / demande_adhesion : champs axe et spécialités

Retours utilisateurs PdoC (pôles de concertation) : chaque OSC doit pouvoir
préciser son axe d'intervention et ses spécialités, affichés et recherchables
dans la page de son pôle.

Revision ID: b7c8d9e0f1a2
Revises: 9f3c7a1b2d84
Create Date: 2026-10-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, None] = "9f3c7a1b2d84"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table in ("osc", "demande_adhesion"):
        op.add_column(table, sa.Column("axe", sa.String(length=200), nullable=True))
        op.add_column(table, sa.Column("specialites", sa.TEXT(), nullable=True))


def downgrade() -> None:
    for table in ("osc", "demande_adhesion"):
        op.drop_column(table, "specialites")
        op.drop_column(table, "axe")
