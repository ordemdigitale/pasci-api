"""add pole concertation fields

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-23

"""
from alembic import op
import sqlalchemy as sa

revision = 'd4e5f6a7b8c9'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('pole_concertation', sa.Column('objectifs_annuels', sa.TEXT(), nullable=True))
    op.add_column('pole_concertation', sa.Column('nb_osc_membres', sa.Integer(), nullable=True))
    op.add_column('pole_concertation', sa.Column('regions_influence', sa.TEXT(), nullable=True))
    op.add_column('pole_concertation', sa.Column('realisations', sa.TEXT(), nullable=True))
    op.add_column('pole_concertation', sa.Column('agenda', sa.TEXT(), nullable=True))


def downgrade() -> None:
    op.drop_column('pole_concertation', 'agenda')
    op.drop_column('pole_concertation', 'realisations')
    op.drop_column('pole_concertation', 'regions_influence')
    op.drop_column('pole_concertation', 'nb_osc_membres')
    op.drop_column('pole_concertation', 'objectifs_annuels')
