"""Increase OSC description field length to 500

Revision ID: 4ce88be8194d
Revises: add_ptf_extended_001
Create Date: 2026-01-28 18:05:47.967672

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4ce88be8194d'
down_revision: Union[str, Sequence[str], None] = 'add_ptf_extended_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Increase the length of the description column in the osc table from 100 to 500
    op.alter_column(
        'osc',
        'description',
        type_=sa.String(500),
        existing_type=sa.String(100),
        existing_nullable=True
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Revert the description column back to 100 characters
    op.alter_column(
        'osc',
        'description',
        type_=sa.String(100),
        existing_type=sa.String(500),
        existing_nullable=True
    )
