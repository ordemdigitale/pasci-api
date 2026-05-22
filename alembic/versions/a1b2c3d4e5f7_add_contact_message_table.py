"""add_contact_message_table

Revision ID: a1b2c3d4e5f7
Revises: f2a3b4c5d6e7
Create Date: 2026-05-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, Sequence[str], None] = 'f2a3b4c5d6e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'contact_message',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('categorie_acteur', sa.String(length=100), nullable=True),
        sa.Column('nom', sa.String(length=100), nullable=False),
        sa.Column('prenoms', sa.String(length=150), nullable=False),
        sa.Column('fonction', sa.String(length=150), nullable=True),
        sa.Column('sexe', sa.String(length=20), nullable=True),
        sa.Column('tranche_age', sa.String(length=30), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('contact', sa.String(length=30), nullable=True),
        sa.Column('pays', sa.String(length=100), nullable=True),
        sa.Column('lieu_residence', sa.String(length=150), nullable=True),
        sa.Column('motif', sa.String(length=100), nullable=False),
        sa.Column('message', sa.TEXT(), nullable=True),
        sa.Column('statut', sa.String(length=20), nullable=False, server_default='nouveau'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_contact_message_id', 'contact_message', ['id'])


def downgrade() -> None:
    op.drop_index('ix_contact_message_id', 'contact_message')
    op.drop_table('contact_message')
