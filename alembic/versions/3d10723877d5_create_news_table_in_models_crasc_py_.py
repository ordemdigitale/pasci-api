"""Create News table in models/crasc.py file

Revision ID: 3d10723877d5
Revises: d9e87b34c30c
Create Date: 2026-01-11 13:44:32.633848

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3d10723877d5'
down_revision: Union[str, Sequence[str], None] = 'd9e87b34c30c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
