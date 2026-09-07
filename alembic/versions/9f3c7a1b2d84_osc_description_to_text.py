"""osc.description : varchar(500) -> TEXT

La description saisie dans une demande d'adhésion est un TEXT libre, alors
que osc.description était limitée à 500 caractères. 24 des demandes déjà
approuvées ont une description plus longue (jusqu'à 5243 caractères), ce qui
faisait échouer la création de l'OSC avec StringDataRightTruncationError
au moment de l'approbation.

Revision ID: 9f3c7a1b2d84
Revises: a0b1c2d3e4f5
Create Date: 2026-09-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9f3c7a1b2d84"
down_revision: Union[str, None] = "a0b1c2d3e4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "osc",
        "description",
        existing_type=sa.String(length=500),
        type_=sa.TEXT(),
        existing_nullable=True,
    )


def downgrade() -> None:
    # Tronque les descriptions trop longues avant de rétrécir la colonne
    op.execute("UPDATE osc SET description = left(description, 500) WHERE length(description) > 500")
    op.alter_column(
        "osc",
        "description",
        existing_type=sa.TEXT(),
        type_=sa.String(length=500),
        existing_nullable=True,
    )
