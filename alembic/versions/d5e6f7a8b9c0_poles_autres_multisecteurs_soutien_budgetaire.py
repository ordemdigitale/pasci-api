"""pôles : ajout de « Autres multi-secteurs » et « Soutien budgétaire »

Retours PdoC (harmonisation des domaines prioritaires) : la liste des pôles
de concertation — qui sert de liste des domaines prioritaires à
l'enrôlement — doit comprendre, en plus des pôles existants (Communication ;
Industrie, mines et constructions ; Distribution d'eau et assainissement ;
Transports et entreposage ; Energie, déjà créés), les pôles « Autres
multi-secteurs » et « Soutien budgétaire ».

Idempotent : un pôle n'est créé que si aucun pôle de même nom (sans tenir
compte des accents, de la casse ni de la ponctuation) n'existe déjà.

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-10-08
"""
import re
import unicodedata
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NOUVEAUX_POLES = [
    ("Autres multi-secteurs", "autres-multi-secteurs"),
    ("Soutien budgétaire", "soutien-budgetaire"),
]


def _cle(valeur: str) -> str:
    texte = unicodedata.normalize("NFD", valeur or "")
    texte = "".join(c for c in texte if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", texte.lower()).strip()


def upgrade() -> None:
    conn = op.get_bind()
    existants = {_cle(nom) for (nom,) in conn.execute(sa.text("SELECT name FROM pole_concertation"))}
    for nom, slug in NOUVEAUX_POLES:
        if _cle(nom) in existants:
            continue
        conn.execute(
            sa.text(
                "INSERT INTO pole_concertation (name, slug, is_active, created_at, updated_at) "
                "VALUES (:nom, :slug, true, now(), now())"
            ),
            {"nom": nom, "slug": slug},
        )


def downgrade() -> None:
    # Ne supprime que des pôles restés vides (aucune OSC, aucun sujet)
    conn = op.get_bind()
    for _, slug in NOUVEAUX_POLES:
        conn.execute(
            sa.text(
                """
                DELETE FROM pole_concertation p WHERE p.slug = :slug
                  AND NOT EXISTS (SELECT 1 FROM osc_pole o WHERE o.pole_id = p.id)
                  AND NOT EXISTS (SELECT 1 FROM forum_sujet s WHERE s.pole_id = p.id)
                """
            ),
            {"slug": slug},
        )
