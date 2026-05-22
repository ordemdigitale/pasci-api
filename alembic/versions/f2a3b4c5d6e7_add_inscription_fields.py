"""add_inscription_fields

Revision ID: f2a3b4c5d6e7
Revises: 83359768847f
Create Date: 2026-05-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f2a3b4c5d6e7'
down_revision: Union[str, Sequence[str], None] = '83359768847f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE formation_inscription ADD COLUMN IF NOT EXISTS participant_nom VARCHAR(100)"))
    conn.execute(sa.text("ALTER TABLE formation_inscription ADD COLUMN IF NOT EXISTS participant_prenoms VARCHAR(150)"))
    conn.execute(sa.text("ALTER TABLE formation_inscription ADD COLUMN IF NOT EXISTS participant_phone VARCHAR(30)"))
    conn.execute(sa.text("ALTER TABLE formation_inscription ADD COLUMN IF NOT EXISTS categorie_acteur VARCHAR(100)"))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE formation_inscription DROP COLUMN IF EXISTS categorie_acteur"))
    conn.execute(sa.text("ALTER TABLE formation_inscription DROP COLUMN IF EXISTS participant_phone"))
    conn.execute(sa.text("ALTER TABLE formation_inscription DROP COLUMN IF EXISTS participant_prenoms"))
    conn.execute(sa.text("ALTER TABLE formation_inscription DROP COLUMN IF EXISTS participant_nom"))
