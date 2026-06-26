"""add pole projects and event status

Revision ID: b0c1d2e3f4a5
Revises: a9b0c1d2e3f4
Create Date: 2026-06-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b0c1d2e3f4a5"
down_revision: Union[str, None] = "a9b0c1d2e3f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pole_concertation",
        sa.Column("projets_en_cours", sa.TEXT(), nullable=True),
    )
    op.add_column(
        "evenement",
        sa.Column("statut", sa.String(length=20), server_default="en_cours", nullable=False),
    )
    op.alter_column("evenement", "statut", server_default=None)


def downgrade() -> None:
    op.drop_column("evenement", "statut")
    op.drop_column("pole_concertation", "projets_en_cours")
