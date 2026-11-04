"""formations : formation commune à tous les CRASC

Retours PdoC (Backend/Ajout de formation) : « CRASC associé : ajouter tous
les CRASC permettra à tous les admins de voir les formations communes ».

Revision ID: c9c625bef9fa
Revises: df6e05deb3ad
Create Date: 2026-11-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9c625bef9fa"
down_revision: Union[str, None] = "df6e05deb3ad"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("formations", sa.Column("tous_crasc", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("formations", "tous_crasc")
