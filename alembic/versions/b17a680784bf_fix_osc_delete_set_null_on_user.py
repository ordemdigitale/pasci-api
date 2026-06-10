"""fix_osc_delete_set_null_on_user

Revision ID: b17a680784bf
Revises: c1d2e3f4a5b6
Create Date: 2026-06-09 21:41:06.238810

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b17a680784bf'
down_revision: Union[str, Sequence[str], None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_constraint('user_osc_id_fkey', type_='foreignkey')
        batch_op.create_foreign_key(
            'user_osc_id_fkey', 'osc', ['osc_id'], ['id'], ondelete='SET NULL'
        )


def downgrade() -> None:
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_constraint('user_osc_id_fkey', type_='foreignkey')
        batch_op.create_foreign_key(
            'user_osc_id_fkey', 'osc', ['osc_id'], ['id']
        )
