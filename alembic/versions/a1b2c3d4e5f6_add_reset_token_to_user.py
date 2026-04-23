"""add reset_token to user

Revision ID: a1b2c3d4e5f6
Revises: 950faf4d2d0c
Create Date: 2026-04-23 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '950faf4d2d0c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('user', sa.Column('reset_token', sa.String(255), nullable=True))
    op.add_column('user', sa.Column('reset_token_expires', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('user', 'reset_token_expires')
    op.drop_column('user', 'reset_token')
