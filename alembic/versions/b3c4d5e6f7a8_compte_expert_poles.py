"""compte expert : anime les discussions des pôles de concertation

Retours PdoC (Pôles de concertation) : « créer un compte expert qui animera
des discussions sur les pôles de concertation ». Le compte expert (user.is_expert)
est rattaché aux pôles qu'il anime (user.expert_poles, liste d'ids en JSON).

Revision ID: b3c4d5e6f7a8
Revises: 9ab13c5d7e64
Create Date: 2026-11-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, None] = "9ab13c5d7e64"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user", sa.Column("is_expert", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("user", sa.Column("expert_poles", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("user", "expert_poles")
    op.drop_column("user", "is_expert")
