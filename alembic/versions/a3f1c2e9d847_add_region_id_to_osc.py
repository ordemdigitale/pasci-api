"""add_region_id_to_osc

Revision ID: a3f1c2e9d847
Revises: 6a4bb84ea76f
Create Date: 2026-04-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a3f1c2e9d847'
down_revision: Union[str, Sequence[str], None] = '6a4bb84ea76f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('osc', schema=None) as batch_op:
        batch_op.add_column(sa.Column('region_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_osc_region_id',
            'region',
            ['region_id'],
            ['id'],
            ondelete='SET NULL'
        )


def downgrade() -> None:
    with op.batch_alter_table('osc', schema=None) as batch_op:
        batch_op.drop_constraint('fk_osc_region_id', type_='foreignkey')
        batch_op.drop_column('region_id')
