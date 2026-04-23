"""add don and volontaire tables

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-23

"""
from alembic import op
import sqlalchemy as sa

revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'don',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nom', sa.String(200), nullable=False),
        sa.Column('email', sa.String(200), nullable=False),
        sa.Column('telephone', sa.String(50), nullable=True),
        sa.Column('montant', sa.Integer(), nullable=False),
        sa.Column('message', sa.TEXT(), nullable=True),
        sa.Column('transaction_id', sa.String(100), nullable=True),
        sa.Column('notify_token', sa.String(255), nullable=True),
        sa.Column('payment_url', sa.String(500), nullable=True),
        sa.Column('statut', sa.String(20), nullable=False, server_default='en_attente'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'volontaire',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nom', sa.String(200), nullable=False),
        sa.Column('email', sa.String(200), nullable=False),
        sa.Column('telephone', sa.String(50), nullable=True),
        sa.Column('profession', sa.String(200), nullable=True),
        sa.Column('domaine', sa.String(200), nullable=False),
        sa.Column('disponibilite', sa.String(50), nullable=True),
        sa.Column('motivation', sa.TEXT(), nullable=False),
        sa.Column('statut', sa.String(20), nullable=False, server_default='en_attente'),
        sa.Column('note_admin', sa.TEXT(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('volontaire')
    op.drop_table('don')
