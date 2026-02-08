"""add_type_field_to_documentation

Revision ID: fd54a10e5276
Revises: f4220c83d0ac
Create Date: 2026-02-08 10:53:27.835839

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fd54a10e5276'
down_revision: Union[str, Sequence[str], None] = 'f4220c83d0ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add type column with default value 'documentation'
    op.add_column('documentation', sa.Column('type', sa.String(length=50), nullable=False, server_default='documentation'))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove type column
    op.drop_column('documentation', 'type')
