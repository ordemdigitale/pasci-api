"""Ajout des contacts de l'OSC (président, OSC, contact 1, contact 2)

Revision ID: e7a1b4c90d23
Revises: b7c8d9e0f1a2
Create Date: 2026-10-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e7a1b4c90d23"
down_revision: Union[str, None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COLONNES = ("contact_president", "contact_osc", "contact_1", "contact_2")


def upgrade() -> None:
    existantes = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("osc")}
    for colonne in COLONNES:
        if colonne not in existantes:
            op.add_column("osc", sa.Column(colonne, sa.String(length=100), nullable=True))


def downgrade() -> None:
    for colonne in COLONNES:
        op.drop_column("osc", colonne)
