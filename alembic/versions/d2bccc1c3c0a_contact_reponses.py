"""contact : réponses envoyées depuis le backoffice

Retours PdoC (Messages de contact) : « donner la possibilité de répondre
directement ». Chaque réponse rédigée dans le backoffice est envoyée par email
à l'usager et historisée ici (auteur, contenu, date).

Revision ID: d2bccc1c3c0a
Revises: 55653a22eaa6
Create Date: 2026-11-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d2bccc1c3c0a"
down_revision: Union[str, None] = "55653a22eaa6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "contact_reponse",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("contact_id", sa.Integer(), nullable=False),
        sa.Column("message", sa.TEXT(), nullable=False),
        sa.Column("auteur_id", sa.Uuid(), nullable=True),
        sa.Column("auteur_nom", sa.String(length=200), nullable=True),
        sa.Column("auteur_email", sa.String(length=255), nullable=True),
        sa.Column("envoye", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["contact_id"], ["contact_message.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["auteur_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_contact_reponse_contact_id"), "contact_reponse", ["contact_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_contact_reponse_contact_id"), table_name="contact_reponse")
    op.drop_table("contact_reponse")
