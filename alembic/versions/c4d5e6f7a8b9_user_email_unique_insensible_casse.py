"""user.email : unicité insensible à la casse et aux espaces

Il était possible de créer deux comptes avec le même email écrit
différemment (« Osc@Mail.ci » / « osc@mail.ci » / espace en fin) : la
contrainte UNIQUE de la colonne compare les chaînes au caractère près.

1. Les emails sont ramenés à leur forme canonique (minuscules, sans espaces)
   quand cela ne crée pas de conflit.
2. Un index unique sur lower(btrim(email)) interdit désormais les doublons
   au niveau de la base.

Si des doublons existent déjà, ils ne sont PAS modifiés ni supprimés
(choisir le compte à garder est une décision humaine) : l'index n'est pas
créé, la liste est affichée, et ils sont visibles dans l'admin
(Utilisateurs → « Comptes en double »). Relancer cette migration
(downgrade puis upgrade) une fois les doublons traités crée l'index.

Revision ID: c4d5e6f7a8b9
Revises: f2c8d50a9b41
Create Date: 2026-10-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, None] = "f2c8d50a9b41"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INDEX = "uq_user_email_insensible_casse"


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Normaliser les emails qui n'entrent en conflit avec aucun autre compte
    conn.execute(sa.text(
        """
        UPDATE "user" u SET email = lower(btrim(u.email))
        WHERE u.email <> lower(btrim(u.email))
          AND NOT EXISTS (
            SELECT 1 FROM "user" autre
            WHERE autre.id <> u.id AND lower(btrim(autre.email)) = lower(btrim(u.email))
          )
        """
    ))

    # 2. Doublons existants : signalés, jamais modifiés automatiquement
    doublons = conn.execute(sa.text(
        """
        SELECT lower(btrim(email)) AS email, count(*) AS nb
        FROM "user" GROUP BY lower(btrim(email)) HAVING count(*) > 1
        ORDER BY 1
        """
    )).all()
    if doublons:
        print(
            f"\n[ATTENTION] {len(doublons)} email(s) partagé(s) par plusieurs comptes — "
            "index unique NON créé. À traiter dans l'admin (Utilisateurs → Comptes en double) :"
        )
        for email, nb in doublons:
            print(f"   - {email} : {nb} comptes")
        return

    op.execute(f'CREATE UNIQUE INDEX IF NOT EXISTS {INDEX} ON "user" (lower(btrim(email)))')


def downgrade() -> None:
    op.execute(f"DROP INDEX IF EXISTS {INDEX}")
