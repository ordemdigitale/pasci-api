"""Drop the News table

Revision ID: d9e87b34c30c
Revises: 0622555718e0
Create Date: 2026-01-11 13:35:23.821542

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd9e87b34c30c'
down_revision: Union[str, Sequence[str], None] = '0622555718e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_table('news')


def downgrade() -> None:
    """Downgrade schema."""
    pass
