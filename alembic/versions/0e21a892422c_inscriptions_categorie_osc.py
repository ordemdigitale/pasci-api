"""inscriptions aux formations : catégorie d'acteurs des comptes OSC

Retours PdoC (6. Formations) : le tableau des formés affichait « Non
renseigné » pour les inscriptions faites depuis un compte connecté (la
catégorie n'était pas demandée). Les inscriptions sans catégorie dont l'email
est celui d'un compte rattaché à une OSC passent en « Organisation de la
Société Civile OSC ». La catégorie est désormais obligatoire.

Revision ID: 0e21a892422c
Revises: 247259fb37d3
Create Date: 2026-11-04
"""
from typing import Sequence, Union

from alembic import op


revision: str = "0e21a892422c"
down_revision: Union[str, None] = "247259fb37d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE formation_inscription AS fi
        SET categorie_acteur = 'Organisation de la Société Civile OSC'
        FROM "user" AS u
        WHERE fi.categorie_acteur IS NULL
          AND u.osc_id IS NOT NULL
          AND (fi.user_id = u.id OR lower(btrim(fi.participant_email)) = lower(btrim(u.email)))
        """
    )


def downgrade() -> None:
    # Données : rien à défaire (on ne sait plus quelles lignes étaient vides)
    pass
