"""add FAQ table

Revision ID: f5a6b7c8d9e0
Revises: f4a5b6c7d8e9
Create Date: 2026-06-12 13:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f5a6b7c8d9e0"
down_revision: Union[str, Sequence[str], None] = "f4a5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "faq",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question", sa.String(length=300), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("ordre", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    faq_table = sa.table(
        "faq",
        sa.column("question", sa.String),
        sa.column("answer", sa.Text),
        sa.column("ordre", sa.Integer),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(
        faq_table,
        [
            {
                "question": "Comment puis-je postuler à une offre d'emploi ?",
                "answer": "Pour postuler à une offre d'emploi, veuillez consulter les offres disponibles sur notre site et cliquez sur le bouton Postuler.",
                "ordre": 1,
                "is_active": True,
            },
            {
                "question": "Quel est le processus de recrutement chez PASCI ?",
                "answer": "Le processus de recrutement chez PASCI comprend plusieurs étapes : l'analyse de votre profil, un entretien technique, un entretien RH et enfin une proposition d'embauche.",
                "ordre": 2,
                "is_active": True,
            },
            {
                "question": "Puis-je envoyer une candidature spontanée ?",
                "answer": "Oui, vous pouvez envoyer une candidature spontanée à travers notre formulaire en ligne ou par email à pdoc@plateforme-osci.org.",
                "ordre": 3,
                "is_active": True,
            },
            {
                "question": "Proposez-vous des stages ou des alternances ?",
                "answer": "Oui, PASCI propose des stages et des alternances dans divers domaines techniques et administratifs. Consultez nos offres spécifiques pour plus d'informations.",
                "ordre": 4,
                "is_active": True,
            },
            {
                "question": "Comment savoir si ma candidature a été reçue ?",
                "answer": "Vous recevrez un email de confirmation dès que votre candidature aura été reçue. Si vous ne recevez pas cet email dans les 24 heures suivantes, veuillez nous contacter.",
                "ordre": 5,
                "is_active": True,
            },
            {
                "question": "Quelles sont les valeurs du projet PASCI ?",
                "answer": "Les valeurs du projet PASCI incluent l'innovation technologique, la collaboration interdisciplinaire et le respect de l'environnement.",
                "ordre": 6,
                "is_active": True,
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("faq")
