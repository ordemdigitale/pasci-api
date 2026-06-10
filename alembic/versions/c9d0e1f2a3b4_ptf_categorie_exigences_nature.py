"""ptf: add categorie, rename conseil to exigences_majeures, add nature_relations

Revision ID: c9d0e1f2a3b4
Revises: d8d5371cd618
Create Date: 2026-06-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9d0e1f2a3b4'
down_revision: Union[str, None] = 'd8d5371cd618'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('ptf', schema=None) as batch_op:
        batch_op.add_column(sa.Column('categorie', sa.VARCHAR(length=100), nullable=True))
        batch_op.alter_column('conseil', new_column_name='exigences_majeures')
        batch_op.add_column(sa.Column('nature_relations', sa.TEXT(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('ptf', schema=None) as batch_op:
        batch_op.drop_column('nature_relations')
        batch_op.alter_column('exigences_majeures', new_column_name='conseil')
        batch_op.drop_column('categorie')
