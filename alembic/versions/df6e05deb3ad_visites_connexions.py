"""visites : comptées par connexion et non par IP

Retours PdoC (Statistique de visite) : « comptabiliser les connexions et non
les IP ». visite.session_id reçoit l'identifiant anonyme de connexion tiré par
le navigateur (nouvelle connexion après 30 min d'inactivité).

Revision ID: df6e05deb3ad
Revises: d49096fc87e1
Create Date: 2026-11-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "df6e05deb3ad"
down_revision: Union[str, None] = "d49096fc87e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("visite", sa.Column("session_id", sa.String(length=64), nullable=True))
    op.create_index("ix_visite_session_id", "visite", ["session_id"])
    # Une page comptée une fois par connexion, même si deux appels arrivent ensemble
    op.create_index(
        "uq_visite_session_path", "visite", ["session_id", "path"],
        unique=True, postgresql_where=sa.text("session_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_visite_session_path", table_name="visite")
    op.drop_index("ix_visite_session_id", table_name="visite")
    op.drop_column("visite", "session_id")
