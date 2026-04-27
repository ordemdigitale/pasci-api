"""add is_redacteur and statut_publication

Revision ID: f1a2b3c4d5e6
Revises: e5f6a7b8c9d0
Create Date: 2026-04-25

"""
from alembic import op
import sqlalchemy as sa

revision = 'f1a2b3c4d5e6'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade():
    # is_redacteur sur user
    op.add_column('user', sa.Column('is_redacteur', sa.Boolean(), nullable=False, server_default='false'))

    # statut_publication sur news
    op.add_column('news', sa.Column('statut_publication', sa.String(length=20), nullable=False, server_default='publie'))

    # statut_publication sur jobs
    op.add_column('jobs', sa.Column('statut_publication', sa.String(length=20), nullable=False, server_default='publie'))

    # statut_publication sur formations
    op.add_column('formations', sa.Column('statut_publication', sa.String(length=20), nullable=False, server_default='publie'))

    # statut_publication sur offreprojet
    op.add_column('offreprojet', sa.Column('statut_publication', sa.String(length=20), nullable=False, server_default='publie'))


def downgrade():
    op.drop_column('offreprojet', 'statut_publication')
    op.drop_column('formations', 'statut_publication')
    op.drop_column('jobs', 'statut_publication')
    op.drop_column('news', 'statut_publication')
    op.drop_column('user', 'is_redacteur')
