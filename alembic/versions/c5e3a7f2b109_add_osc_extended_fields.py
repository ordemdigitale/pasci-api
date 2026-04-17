"""add_osc_extended_fields

Revision ID: c5e3a7f2b109
Revises: b7e2d4f1c983
Create Date: 2026-04-17 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'c5e3a7f2b109'
down_revision: Union[str, Sequence[str], None] = 'b7e2d4f1c983'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('osc', schema=None) as batch_op:
        # Extra domaines prioritaires
        batch_op.add_column(sa.Column('domaine_prioritaire_2',      sa.String(200),  nullable=True))
        batch_op.add_column(sa.Column('domaine_prioritaire_3',      sa.String(200),  nullable=True))
        batch_op.add_column(sa.Column('domaine_prioritaire_4',      sa.String(200),  nullable=True))
        # Membres / personnes
        batch_op.add_column(sa.Column('nb_femmes_membres',          sa.Integer(),    nullable=True))
        batch_op.add_column(sa.Column('nb_membres_jeunes',          sa.Integer(),    nullable=True))
        batch_op.add_column(sa.Column('nb_membres_be',              sa.Integer(),    nullable=True))
        batch_op.add_column(sa.Column('nb_personnes_engagees',      sa.Integer(),    nullable=True))
        batch_op.add_column(sa.Column('nb_beneficiaires',           sa.Integer(),    nullable=True))
        batch_op.add_column(sa.Column('nb_activites',               sa.Integer(),    nullable=True))
        # Financement
        batch_op.add_column(sa.Column('type_financement',           sa.String(500),  nullable=True))
        batch_op.add_column(sa.Column('etat_cotisations',           sa.String(200),  nullable=True))
        batch_op.add_column(sa.Column('montant_cotisation',         sa.Integer(),    nullable=True))
        # Gouvernance
        batch_op.add_column(sa.Column('sexe_president',             sa.String(20),   nullable=True))
        batch_op.add_column(sa.Column('mode_designation_president', sa.String(200),  nullable=True))
        batch_op.add_column(sa.Column('duree_mandat_be',            sa.String(100),  nullable=True))
        batch_op.add_column(sa.Column('adhesion_crasc',             sa.Boolean(),    nullable=True))
        # Réseau / texte libre
        batch_op.add_column(sa.Column('reseau_appartenance',        sa.Text(),       nullable=True))
        batch_op.add_column(sa.Column('secteurs_activites',         sa.Text(),       nullable=True))
        batch_op.add_column(sa.Column('populations_cibles',         sa.Text(),       nullable=True))
        batch_op.add_column(sa.Column('savoir_faire',               sa.Text(),       nullable=True))
        batch_op.add_column(sa.Column('difficultes',                sa.Text(),       nullable=True))
        batch_op.add_column(sa.Column('recommandations',            sa.Text(),       nullable=True))
        # Sources de financement (booléens)
        batch_op.add_column(sa.Column('financement_cotisation',     sa.Boolean(),    nullable=True))
        batch_op.add_column(sa.Column('financement_dons',           sa.Boolean(),    nullable=True))
        batch_op.add_column(sa.Column('financement_legs',           sa.Boolean(),    nullable=True))
        batch_op.add_column(sa.Column('financement_collectivites',  sa.Boolean(),    nullable=True))
        batch_op.add_column(sa.Column('financement_fonds_propres',  sa.Boolean(),    nullable=True))
        batch_op.add_column(sa.Column('financement_ong_intl',       sa.Boolean(),    nullable=True))
        batch_op.add_column(sa.Column('financement_multilateral',   sa.Boolean(),    nullable=True))


def downgrade() -> None:
    cols = [
        'domaine_prioritaire_2', 'domaine_prioritaire_3', 'domaine_prioritaire_4',
        'nb_femmes_membres', 'nb_membres_jeunes', 'nb_membres_be',
        'nb_personnes_engagees', 'nb_beneficiaires', 'nb_activites',
        'type_financement', 'etat_cotisations', 'montant_cotisation',
        'sexe_president', 'mode_designation_president', 'duree_mandat_be',
        'adhesion_crasc', 'reseau_appartenance', 'secteurs_activites',
        'populations_cibles', 'savoir_faire', 'difficultes', 'recommandations',
        'financement_cotisation', 'financement_dons', 'financement_legs',
        'financement_collectivites', 'financement_fonds_propres',
        'financement_ong_intl', 'financement_multilateral',
    ]
    with op.batch_alter_table('osc', schema=None) as batch_op:
        for col in cols:
            batch_op.drop_column(col)
