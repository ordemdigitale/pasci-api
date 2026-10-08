"""pôles : fusion « Gouvernement et Société Civile » + « Prévention et règlement
des conflits, paix et sécurité » → « Gouvernement, société civile, paix et sécurité »

Retours PdoC : fusion demandée des deux pôles. Même logique que l'action
admin POST /forum/poles/{slug}/fusionner :
- les OSC membres, sujets de discussion et sondages du pôle « Prévention… »
  passent dans le pôle « Gouvernement et Société Civile », renommé ;
- les domaines prioritaires des OSC et des demandes d'adhésion qui citaient
  l'un des deux anciens noms prennent le nouveau nom ;
- le pôle « Prévention… » est désactivé (conservé pour l'historique).

Idempotente : ne fait rien si la fusion a déjà été faite (pôle fusionné déjà
présent, ou pôle source déjà désactivé / introuvable).

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-10-08
"""
import re
import unicodedata
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CIBLE = "Gouvernement et Société Civile"
SOURCE = "Prévention et règlement des conflits, paix et sécurité"
NOUVEAU_NOM = "Gouvernement, société civile, paix et sécurité"
NOUVEAU_SLUG = "gouvernement-societe-civile-paix-et-securite"
DOMAINES = ["domaine_prioritaire", "domaine_prioritaire_2", "domaine_prioritaire_3",
            "domaine_prioritaire_4", "domaine_prioritaire_5"]


def _cle(valeur) -> str:
    texte = unicodedata.normalize("NFD", valeur or "")
    texte = "".join(c for c in texte if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", texte.lower()).strip()


def _pole(conn, nom):
    for pid, name, actif in conn.execute(sa.text("SELECT id, name, is_active FROM pole_concertation")):
        if _cle(name) == _cle(nom):
            return pid, name, actif
    return None


def upgrade() -> None:
    conn = op.get_bind()

    if _pole(conn, NOUVEAU_NOM):
        print(f"[fusion] « {NOUVEAU_NOM} » existe déjà : rien à faire.")
        return
    cible = _pole(conn, CIBLE)
    source = _pole(conn, SOURCE)
    if not cible:
        print(f"[fusion] pôle « {CIBLE} » introuvable : fusion à faire depuis l'admin.")
        return

    cible_id = cible[0]
    if source and source[2]:
        source_id = source[0]
        # 1. OSC membres : passent dans la cible (sans doublon de lien)
        conn.execute(sa.text(
            "INSERT INTO osc_pole (osc_id, pole_id) "
            "SELECT osc_id, :cible FROM osc_pole WHERE pole_id = :source "
            "AND osc_id NOT IN (SELECT osc_id FROM osc_pole WHERE pole_id = :cible)"
        ), {"cible": cible_id, "source": source_id})
        conn.execute(sa.text("DELETE FROM osc_pole WHERE pole_id = :source"), {"source": source_id})
        # 2. Discussions et sondages
        conn.execute(sa.text("UPDATE forum_sujet SET pole_id = :cible WHERE pole_id = :source"),
                     {"cible": cible_id, "source": source_id})
        conn.execute(sa.text("UPDATE pole_sondage SET pole_id = :cible WHERE pole_id = :source"),
                     {"cible": cible_id, "source": source_id})
        # 3. Source désactivée, pas supprimée
        conn.execute(sa.text("UPDATE pole_concertation SET is_active = false WHERE id = :source"),
                     {"source": source_id})

    # 4. Pôle fusionné renommé
    conn.execute(sa.text("UPDATE pole_concertation SET name = :nom, slug = :slug, updated_at = now() WHERE id = :id"),
                 {"nom": NOUVEAU_NOM, "slug": NOUVEAU_SLUG, "id": cible_id})

    # 5. Domaines prioritaires des OSC et des demandes d'adhésion
    anciens = {_cle(CIBLE), _cle(SOURCE)}
    for table in ("osc", "demande_adhesion"):
        lignes = conn.execute(sa.text(f"SELECT id, {', '.join(DOMAINES)} FROM {table}")).all()
        for ligne in lignes:
            valeurs = {col: NOUVEAU_NOM for col, val in zip(DOMAINES, ligne[1:]) if val and _cle(val) in anciens}
            if valeurs:
                sets = ", ".join(f"{col} = :{col}" for col in valeurs)
                conn.execute(sa.text(f"UPDATE {table} SET {sets} WHERE id = :id"), {**valeurs, "id": ligne[0]})

    print(f"[fusion] « {SOURCE} » fusionné dans « {NOUVEAU_NOM} ».")


def downgrade() -> None:
    # Une fusion ne se défait pas automatiquement (les membres ont été regroupés).
    pass
