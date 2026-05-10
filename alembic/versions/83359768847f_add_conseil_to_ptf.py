"""add_conseil_to_ptf

Revision ID: 83359768847f
Revises: 143439c32790
Create Date: 2026-05-10 13:17:27.320895

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '83359768847f'
down_revision: Union[str, Sequence[str], None] = '143439c32790'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('ptf', schema=None) as batch_op:
        batch_op.add_column(sa.Column('conseil', sa.TEXT(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('ptf', schema=None) as batch_op:
        batch_op.drop_column('conseil')
