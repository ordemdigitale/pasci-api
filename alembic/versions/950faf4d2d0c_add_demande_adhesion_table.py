"""add demande adhesion table

Revision ID: 950faf4d2d0c
Revises: d1f4b8e2c310
Create Date: 2026-04-23 09:54:11.504967

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '950faf4d2d0c'
down_revision: Union[str, Sequence[str], None] = 'd1f4b8e2c310'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'demande_adhesion',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nom_organisation', sa.String(length=200), nullable=False),
        sa.Column('type_organisation', sa.String(length=100), nullable=False),
        sa.Column('region', sa.String(length=100), nullable=False),
        sa.Column('ville', sa.String(length=100), nullable=True),
        sa.Column('email', sa.String(length=200), nullable=False),
        sa.Column('telephone', sa.String(length=50), nullable=False),
        sa.Column('description', sa.TEXT(), nullable=True),
        sa.Column('motivation', sa.TEXT(), nullable=False),
        sa.Column('statut', sa.String(length=20), nullable=False, server_default='en_attente'),
        sa.Column('note_admin', sa.TEXT(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('demande_adhesion')
