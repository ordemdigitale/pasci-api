"""add_categorie_to_formation

Revision ID: d8d5371cd618
Revises: b17a680784bf
Create Date: 2026-06-09 22:33:52.148497

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8d5371cd618'
down_revision: Union[str, Sequence[str], None] = 'b17a680784bf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('formations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('categorie', sa.VARCHAR(length=200), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('formations', schema=None) as batch_op:
        batch_op.drop_column('categorie')
