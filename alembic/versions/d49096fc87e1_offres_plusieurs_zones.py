"""offres de projet : plusieurs zones d'exécution

Retours PdoC (Appel à projets) : « donner la possibilité d'ajouter plusieurs
zones d'exécution d'un projet ». Les zones restent dans offreprojet.zone,
séparées par des virgules ; la colonne passe en TEXT (100 caractères ne
suffisaient pas pour plusieurs régions).

Revision ID: d49096fc87e1
Revises: 0e21a892422c
Create Date: 2026-11-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d49096fc87e1"
down_revision: Union[str, None] = "0e21a892422c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("offreprojet", "zone", type_=sa.TEXT(), existing_type=sa.String(length=100), existing_nullable=False)


def downgrade() -> None:
    op.execute("UPDATE offreprojet SET zone = left(zone, 100)")
    op.alter_column("offreprojet", "zone", type_=sa.String(length=100), existing_type=sa.TEXT(), existing_nullable=False)
