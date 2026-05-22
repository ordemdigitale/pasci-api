"""add_inscription_fields

Revision ID: f2a3b4c5d6e7
Revises: 6a4bb84ea76f
Create Date: 2026-05-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f2a3b4c5d6e7'
down_revision: Union[str, Sequence[str], None] = '83359768847f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('formation_inscription', schema=None) as batch_op:
        batch_op.add_column(sa.Column('participant_nom', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('participant_prenoms', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('participant_phone', sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column('categorie_acteur', sa.String(length=100), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('formation_inscription', schema=None) as batch_op:
        batch_op.drop_column('categorie_acteur')
        batch_op.drop_column('participant_phone')
        batch_op.drop_column('participant_prenoms')
        batch_op.drop_column('participant_nom')
