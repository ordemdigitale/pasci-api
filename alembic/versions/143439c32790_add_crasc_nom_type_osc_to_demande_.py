"""add_crasc_nom_type_osc_to_demande_adhesion

Revision ID: 143439c32790
Revises: 0f57c37b9552
Create Date: 2026-05-10 08:11:45.653209

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '143439c32790'
down_revision: Union[str, Sequence[str], None] = '0f57c37b9552'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('demande_adhesion', schema=None) as batch_op:
        batch_op.add_column(sa.Column('crasc_nom', sa.String(200), nullable=True))
        batch_op.add_column(sa.Column('type_osc', sa.String(100), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('demande_adhesion', schema=None) as batch_op:
        batch_op.drop_column('type_osc')
        batch_op.drop_column('crasc_nom')
