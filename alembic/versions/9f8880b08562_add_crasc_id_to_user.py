"""add_crasc_id_to_user

Revision ID: 9f8880b08562
Revises: f1a2b3c4d5e6
Create Date: 2026-05-06 08:32:18.714000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9f8880b08562'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('crasc_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_user_crasc_id', 'crasc', ['crasc_id'], ['id'])


def downgrade() -> None:
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_constraint('fk_user_crasc_id', type_='foreignkey')
        batch_op.drop_column('crasc_id')
