"""Contacts de l'OSC dès la demande d'adhésion

Les quatre contacts existaient déjà sur l'OSC mais pas sur la demande : une
OSC nouvellement enrôlée arrivait donc avec ces champs vides. Ils sont
désormais saisis à l'enrôlement et recopiés sur l'OSC à la validation.

Revision ID: f2c8d50a9b41
Revises: e7a1b4c90d23
Create Date: 2026-10-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f2c8d50a9b41"
down_revision: Union[str, None] = "e7a1b4c90d23"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COLONNES = ("contact_president", "contact_osc", "contact_1", "contact_2")


def upgrade() -> None:
    existantes = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("demande_adhesion")}
    for colonne in COLONNES:
        if colonne not in existantes:
            op.add_column("demande_adhesion", sa.Column(colonne, sa.String(length=100), nullable=True))


def downgrade() -> None:
    for colonne in COLONNES:
        op.drop_column("demande_adhesion", colonne)
