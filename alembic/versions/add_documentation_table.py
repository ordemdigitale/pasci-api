"""add documentation table

Revision ID: add_documentation_001
Revises: fa67f15e4823
Create Date: 2026-01-25 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'add_documentation_001'
down_revision: Union[str, None] = 'fa67f15e4823'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('documentation',
    sa.Column('title', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('category', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
    sa.Column('file_path', sqlmodel.sql.sqltypes.AutoString(length=2048), nullable=True),
    sa.Column('file_type', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True),
    sa.Column('file_size', sa.Integer(), nullable=True),
    sa.Column('thumbnail_path', sqlmodel.sql.sqltypes.AutoString(length=2048), nullable=True),
    sa.Column('crasc_id', sa.Integer(), nullable=True),
    sa.Column('osc_id', sa.Integer(), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('slug', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['crasc_id'], ['crasc.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['osc_id'], ['osc.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('slug'),
    sa.UniqueConstraint('title')
    )
    with op.batch_alter_table('documentation', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_documentation_title'), ['title'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('documentation', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_documentation_title'))
    op.drop_table('documentation')
