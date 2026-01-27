"""add extended fields to PTF model

Revision ID: add_ptf_extended_001
Revises: add_documentation_001
Create Date: 2026-01-27 21:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'add_ptf_extended_001'
down_revision: Union[str, None] = 'add_documentation_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add extended fields to PTF model."""
    # Add new columns to ptf table
    with op.batch_alter_table('ptf', schema=None) as batch_op:
        # Descriptions
        batch_op.add_column(sa.Column('mission', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('vision', sa.Text(), nullable=True))

        # Images
        batch_op.add_column(sa.Column('cover_path', sqlmodel.sql.sqltypes.AutoString(length=2048), nullable=True))

        # Contact information
        batch_op.add_column(sa.Column('website', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True))
        batch_op.add_column(sa.Column('email', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True))
        batch_op.add_column(sa.Column('phone', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True))
        batch_op.add_column(sa.Column('address', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True))

        # General information
        batch_op.add_column(sa.Column('pays', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True))
        batch_op.add_column(sa.Column('date_creation', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True))

        # Domaines d'intervention (JSON string)
        batch_op.add_column(sa.Column('domaines', sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove extended fields from PTF model."""
    # Remove columns from ptf table
    with op.batch_alter_table('ptf', schema=None) as batch_op:
        batch_op.drop_column('domaines')
        batch_op.drop_column('date_creation')
        batch_op.drop_column('pays')
        batch_op.drop_column('address')
        batch_op.drop_column('phone')
        batch_op.drop_column('email')
        batch_op.drop_column('website')
        batch_op.drop_column('cover_path')
        batch_op.drop_column('vision')
        batch_op.drop_column('mission')
