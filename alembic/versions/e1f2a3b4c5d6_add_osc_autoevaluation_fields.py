"""add OSC self-evaluation fields

Revision ID: e1f2a3b4c5d6
Revises: c9d0e1f2a3b4
Create Date: 2026-06-11 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("osc", schema=None) as batch_op:
        batch_op.add_column(sa.Column("type_document_formalisation", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("existence_siege", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("manuel_procedures", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("plan_action", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("rapports_annuels", sa.Boolean(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("osc", schema=None) as batch_op:
        batch_op.drop_column("rapports_annuels")
        batch_op.drop_column("plan_action")
        batch_op.drop_column("manuel_procedures")
        batch_op.drop_column("existence_siege")
        batch_op.drop_column("type_document_formalisation")
