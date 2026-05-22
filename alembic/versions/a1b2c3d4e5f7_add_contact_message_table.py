"""add_contact_message_table

Revision ID: a1b2c3d4e5f7
Revises: f2a3b4c5d6e7
Create Date: 2026-05-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, Sequence[str], None] = 'f2a3b4c5d6e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS contact_message (
            id SERIAL NOT NULL,
            categorie_acteur VARCHAR(100),
            nom VARCHAR(100) NOT NULL,
            prenoms VARCHAR(150) NOT NULL,
            fonction VARCHAR(150),
            sexe VARCHAR(20),
            tranche_age VARCHAR(30),
            email VARCHAR(255) NOT NULL,
            contact VARCHAR(30),
            pays VARCHAR(100),
            lieu_residence VARCHAR(150),
            motif VARCHAR(100) NOT NULL,
            message TEXT,
            statut VARCHAR(20) NOT NULL DEFAULT 'nouveau',
            created_at TIMESTAMPTZ DEFAULT now(),
            PRIMARY KEY (id)
        )
    """))
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_contact_message_id ON contact_message (id)"
    ))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_contact_message_id"))
    conn.execute(sa.text("DROP TABLE IF EXISTS contact_message"))
