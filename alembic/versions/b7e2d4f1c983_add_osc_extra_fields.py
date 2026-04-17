"""add_osc_extra_fields

Revision ID: b7e2d4f1c983
Revises: a3f1c2e9d847
Create Date: 2026-04-17 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b7e2d4f1c983'
down_revision: Union[str, Sequence[str], None] = 'a3f1c2e9d847'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('osc', schema=None) as batch_op:
        batch_op.add_column(sa.Column('website',           sa.String(500),  nullable=True))
        batch_op.add_column(sa.Column('reseaux_sociaux',   sa.Text(),        nullable=True))
        batch_op.add_column(sa.Column('date_creation',     sa.String(30),   nullable=True))
        batch_op.add_column(sa.Column('numero_recepisse',  sa.String(200),  nullable=True))
        batch_op.add_column(sa.Column('niveau_couverture', sa.String(100),  nullable=True))
        batch_op.add_column(sa.Column('zone_couverture',   sa.String(200),  nullable=True))
        batch_op.add_column(sa.Column('categorie',         sa.String(200),  nullable=True))
        batch_op.add_column(sa.Column('domaine_prioritaire', sa.String(200), nullable=True))
        batch_op.add_column(sa.Column('nb_membres',        sa.Integer(),    nullable=True))
        batch_op.add_column(sa.Column('budget_annuel',     sa.BigInteger(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('osc', schema=None) as batch_op:
        for col in ['website', 'reseaux_sociaux', 'date_creation', 'numero_recepisse',
                    'niveau_couverture', 'zone_couverture', 'categorie',
                    'domaine_prioritaire', 'nb_membres', 'budget_annuel']:
            batch_op.drop_column(col)
