"""taskforce : membres, espace documentaire, zones et les cinq taskforces régionales

Cahier des charges PdoC : une lucarne « Membres » (titre, fonction, contact,
zone CRASC, groupes thématiques, rôle), un espace documentaire structuré
hébergé sur la plateforme, et cinq taskforces thématiques régionales (Nord,
Sud, Est, Ouest, Centre) créées d'emblée, d'autres restant créables.

Revision ID: 2ab02ef74094
Revises: d75dd7ee7dd5
Create Date: 2026-11-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2ab02ef74094"
down_revision: Union[str, None] = "d75dd7ee7dd5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ZONES = ["Nord", "Sud", "Est", "Ouest", "Centre"]


def upgrade() -> None:
    # ── Zone couverte par la task force ───────────────────────────────────
    op.add_column("task_force_osc", sa.Column("zone", sa.String(length=50), nullable=True))
    op.create_index(op.f("ix_task_force_osc_zone"), "task_force_osc", ["zone"])

    # ── Membres : des personnes, représentant une OSC ─────────────────────
    op.create_table(
        "task_force_membre",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_force_id", sa.Integer(), nullable=False),
        sa.Column("osc_id", sa.Integer(), nullable=True),
        sa.Column("titre", sa.String(length=100), nullable=True),
        sa.Column("nom", sa.String(length=200), nullable=False),
        sa.Column("fonction", sa.String(length=200), nullable=True),
        sa.Column("contact", sa.String(length=100), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("zone_crasc", sa.String(length=100), nullable=True),
        sa.Column("groupes_thematiques", sa.String(length=500), nullable=True),
        sa.Column("role", sa.String(length=100), nullable=True),
        sa.Column("est_coordonnateur", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("ordre", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["task_force_id"], ["task_force_osc.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["osc_id"], ["osc.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_task_force_membre_task_force_id"), "task_force_membre", ["task_force_id"])
    op.create_index(op.f("ix_task_force_membre_osc_id"), "task_force_membre", ["osc_id"])
    op.create_index(op.f("ix_task_force_membre_est_coordonnateur"), "task_force_membre", ["est_coordonnateur"])

    # ── Espace documentaire ───────────────────────────────────────────────
    op.create_table(
        "task_force_document",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_force_id", sa.Integer(), nullable=True),
        sa.Column("categorie", sa.String(length=100), nullable=False),
        sa.Column("sous_categorie", sa.String(length=150), nullable=True),
        sa.Column("titre", sa.String(length=300), nullable=False),
        sa.Column("description", sa.TEXT(), nullable=True),
        sa.Column("fichier_path", sa.String(length=2048), nullable=True),
        sa.Column("fichier_nom", sa.String(length=300), nullable=True),
        sa.Column("taille_octets", sa.Integer(), nullable=True),
        sa.Column("auteur_id", sa.Uuid(), nullable=True),
        sa.Column("auteur_nom", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["task_force_id"], ["task_force_osc.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["auteur_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_task_force_document_task_force_id"), "task_force_document", ["task_force_id"])
    op.create_index(op.f("ix_task_force_document_categorie"), "task_force_document", ["categorie"])
    op.create_index(op.f("ix_task_force_document_sous_categorie"), "task_force_document", ["sous_categorie"])
    op.create_index(op.f("ix_task_force_document_created_at"), "task_force_document", ["created_at"])

    # ── Les cinq taskforces thématiques régionales ────────────────────────
    for ordre, zone in enumerate(ZONES):
        op.execute(
            sa.text(
                """
                INSERT INTO task_force_osc (nom, slug, thematique, zone, ordre, actif, created_at, updated_at)
                SELECT :nom, :slug, NULL, :zone, :ordre, true, now(), now()
                WHERE NOT EXISTS (SELECT 1 FROM task_force_osc WHERE nom = :nom)
                """
            ).bindparams(
                nom=f"Taskforce Thématique {zone}",
                slug=f"taskforce-thematique-{zone.lower()}",
                zone=zone,
                ordre=ordre,
            )
        )


def downgrade() -> None:
    op.execute("DELETE FROM task_force_osc WHERE nom LIKE 'Taskforce Thématique %'")
    for index in ("created_at", "sous_categorie", "categorie", "task_force_id"):
        op.drop_index(op.f(f"ix_task_force_document_{index}"), table_name="task_force_document")
    op.drop_table("task_force_document")
    for index in ("est_coordonnateur", "osc_id", "task_force_id"):
        op.drop_index(op.f(f"ix_task_force_membre_{index}"), table_name="task_force_membre")
    op.drop_table("task_force_membre")
    op.drop_index(op.f("ix_task_force_osc_zone"), table_name="task_force_osc")
    op.drop_column("task_force_osc", "zone")
