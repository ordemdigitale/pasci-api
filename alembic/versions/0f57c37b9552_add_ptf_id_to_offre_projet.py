"""add_ptf_id_to_offre_projet

Revision ID: 0f57c37b9552
Revises: 9f8880b08562
Create Date: 2026-05-06 10:59:08.655806

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0f57c37b9552'
down_revision: Union[str, Sequence[str], None] = '9f8880b08562'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('offreprojet', schema=None) as batch_op:
        batch_op.add_column(sa.Column('ptf_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_offreprojet_ptf_id', 'ptf', ['ptf_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    with op.batch_alter_table('offreprojet', schema=None) as batch_op:
        batch_op.drop_constraint('fk_offreprojet_ptf_id', type_='foreignkey')
        batch_op.drop_column('ptf_id')
