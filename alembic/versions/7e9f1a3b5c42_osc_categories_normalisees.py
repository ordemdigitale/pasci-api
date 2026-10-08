"""osc : catégories (OdF, OdJ, OPSH, mixte) ramenées au code interne

Retours PdoC (section 8, Administration générale) : vérifier le tagging des
OdF, OdJ, OPSH et faîtières. D'anciennes fiches portaient le libellé complet
ou le sigle (« Organisation de femmes », « ODJ »…) au lieu du code : elles
sont ramenées au code interne pour que filtres, tris et étiquettes soient
cohérents. Les valeurs non reconnues sont laissées telles quelles.
La faîtière n'est pas stockée : elle se déduit du niveau de regroupement.

Revision ID: 7e9f1a3b5c42
Revises: 6d8e0f2a4b31
Create Date: 2026-10-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.services.osc_etiquettes import code_categorie


revision: str = "7e9f1a3b5c42"
down_revision: Union[str, None] = "6d8e0f2a4b31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    for table in ("osc", "demande_adhesion"):
        valeurs = bind.execute(sa.text(
            f"SELECT DISTINCT categorie FROM {table} WHERE categorie IS NOT NULL AND categorie <> ''"
        )).scalars().all()
        for valeur in valeurs:
            code = code_categorie(valeur)
            if code and code != valeur:
                bind.execute(
                    sa.text(f"UPDATE {table} SET categorie = :code WHERE categorie = :valeur"),
                    {"code": code, "valeur": valeur},
                )


def downgrade() -> None:
    # Normalisation de données : pas de retour arrière (les anciennes écritures sont équivalentes).
    pass
