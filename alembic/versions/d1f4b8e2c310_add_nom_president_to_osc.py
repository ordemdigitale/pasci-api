"""add_nom_president_to_osc

Revision ID: d1f4b8e2c310
Revises: c5e3a7f2b109
Create Date: 2026-04-17 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'd1f4b8e2c310'
down_revision: Union[str, Sequence[str], None] = 'c5e3a7f2b109'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('osc', schema=None) as batch_op:
        batch_op.add_column(sa.Column('nom_president', sa.String(200), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('osc', schema=None) as batch_op:
        batch_op.drop_column('nom_president')
