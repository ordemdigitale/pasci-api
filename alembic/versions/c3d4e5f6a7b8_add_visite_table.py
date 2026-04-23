"""add visite table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-23

"""
from alembic import op
import sqlalchemy as sa

revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'visite',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('path', sa.String(500), nullable=False),
        sa.Column('ip_hash', sa.String(64), nullable=False),
        sa.Column('date_visite', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_visite_date', 'visite', ['date_visite'])
    op.create_index('ix_visite_ip_path_date', 'visite', ['ip_hash', 'path', 'date_visite'])


def downgrade() -> None:
    op.drop_index('ix_visite_ip_path_date', 'visite')
    op.drop_index('ix_visite_date', 'visite')
    op.drop_table('visite')
