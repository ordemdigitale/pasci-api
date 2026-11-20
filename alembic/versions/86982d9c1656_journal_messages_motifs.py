"""historique d'actions, messages groupés, motifs de rejet et région manquante

Retours PdoC :
- historique des actions (qui a fait quoi, et quand) ;
- messages groupés adressés à une sélection d'OSC ou de PTF ;
- motifs de rejet cochés par le point focal sur un article ;
- « Ferkessédougou ne figure pas dans les régions » du formulaire OSC.

Revision ID: 86982d9c1656
Revises: 47b020d90319
Create Date: 2026-11-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "86982d9c1656"
down_revision: Union[str, None] = "47b020d90319"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Historique des actions ────────────────────────────────────────────
    op.create_table(
        "journal_action",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("utilisateur", sa.String(length=255), nullable=True),
        sa.Column("action", sa.String(length=60), nullable=False),
        sa.Column("cible_type", sa.String(length=50), nullable=True),
        sa.Column("cible_id", sa.String(length=100), nullable=True),
        sa.Column("cible_libelle", sa.String(length=300), nullable=True),
        sa.Column("details", sa.TEXT(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_journal_action_user_id"), "journal_action", ["user_id"])
    op.create_index(op.f("ix_journal_action_action"), "journal_action", ["action"])
    op.create_index(op.f("ix_journal_action_cible_type"), "journal_action", ["cible_type"])
    op.create_index(op.f("ix_journal_action_created_at"), "journal_action", ["created_at"])

    # ── Messages groupés ──────────────────────────────────────────────────
    op.create_table(
        "message_groupe",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("objet", sa.String(length=200), nullable=False),
        sa.Column("message", sa.TEXT(), nullable=False),
        sa.Column("criteres", sa.TEXT(), nullable=True),
        sa.Column("lien", sa.String(length=500), nullable=True),
        sa.Column("nb_destinataires", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("nb_emails", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("nb_notifications", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("auteur_id", sa.Uuid(), nullable=True),
        sa.Column("auteur_nom", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["auteur_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_message_groupe_created_at"), "message_groupe", ["created_at"])

    # ── Motifs de rejet d'une actualité ───────────────────────────────────
    op.add_column("news", sa.Column("motifs_rejet", sa.String(length=500), nullable=True))
    op.add_column("news", sa.Column("motif_rejet_detail", sa.TEXT(), nullable=True))

    # ── Région manquante du formulaire OSC ────────────────────────────────
    # Rattachée au même CRASC que Tchologo, sa région administrative.
    op.execute(
        """
        INSERT INTO region (name, slug, crasc_id, created_at, updated_at)
        SELECT 'Ferkessédougou', 'ferkessedougou',
               (SELECT crasc_id FROM region WHERE name ILIKE 'Tchologo' LIMIT 1),
               now(), now()
        WHERE NOT EXISTS (SELECT 1 FROM region WHERE name ILIKE 'Ferkessédougou')
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM region WHERE name ILIKE 'Ferkessédougou'")
    op.drop_column("news", "motif_rejet_detail")
    op.drop_column("news", "motifs_rejet")
    op.drop_index(op.f("ix_message_groupe_created_at"), table_name="message_groupe")
    op.drop_table("message_groupe")
    for index in ("created_at", "cible_type", "action", "user_id"):
        op.drop_index(op.f(f"ix_journal_action_{index}"), table_name="journal_action")
    op.drop_table("journal_action")
