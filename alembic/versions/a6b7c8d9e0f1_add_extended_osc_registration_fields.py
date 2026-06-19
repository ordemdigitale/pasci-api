"""add extended OSC registration fields

Revision ID: a6b7c8d9e0f1
Revises: f5a6b7c8d9e0
Create Date: 2026-06-18 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a6b7c8d9e0f1"
down_revision: Union[str, Sequence[str], None] = "f5a6b7c8d9e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


OSC_COLUMNS = [
    sa.Column("sigle", sa.String(length=100), nullable=True),
    sa.Column("region_nom", sa.String(length=150), nullable=True),
    sa.Column("departement", sa.String(length=150), nullable=True),
    sa.Column("sous_prefecture", sa.String(length=150), nullable=True),
    sa.Column("origine_organisation", sa.String(length=50), nullable=True),
    sa.Column("domaine_prioritaire_5", sa.String(length=200), nullable=True),
    sa.Column("nb_hommes_membres", sa.Integer(), nullable=True),
    sa.Column("nb_membres_handicap", sa.Integer(), nullable=True),
    sa.Column("nombre_mandats_be", sa.Integer(), nullable=True),
    sa.Column("nb_femmes_beneficiaires", sa.Integer(), nullable=True),
    sa.Column("nb_jeunes_beneficiaires", sa.Integer(), nullable=True),
    sa.Column("nb_beneficiaires_handicap", sa.Integer(), nullable=True),
    sa.Column("adhesion_crasc_statut", sa.String(length=20), nullable=True),
    sa.Column("organes_gouvernance", sa.Text(), nullable=True),
    sa.Column("pays_couverture", sa.Text(), nullable=True),
    sa.Column("nb_cdi", sa.Integer(), nullable=True),
    sa.Column("nb_cdd", sa.Integer(), nullable=True),
    sa.Column("date_designation_responsable", sa.String(length=30), nullable=True),
    sa.Column("date_prochaine_designation", sa.String(length=30), nullable=True),
    sa.Column("plan_action_annee_cours", sa.Boolean(), nullable=True),
    sa.Column("plan_action_annee_cours_details", sa.Text(), nullable=True),
    sa.Column("date_derniere_activite", sa.String(length=30), nullable=True),
    sa.Column("recommandations_2", sa.Text(), nullable=True),
]

DEMANDE_COLUMNS = [
    sa.Column("sigle", sa.String(length=100), nullable=True),
    sa.Column("departement", sa.String(length=150), nullable=True),
    sa.Column("sous_prefecture", sa.String(length=150), nullable=True),
    sa.Column("origine_organisation", sa.String(length=50), nullable=True),
    sa.Column("type_document_formalisation", sa.String(length=50), nullable=True),
    sa.Column("existence_siege", sa.Boolean(), nullable=True),
    sa.Column("categorie", sa.String(length=100), nullable=True),
    sa.Column("niveau_regroupement", sa.String(length=30), nullable=True),
    sa.Column("domaine_prioritaire", sa.String(length=200), nullable=True),
    sa.Column("domaine_prioritaire_2", sa.String(length=200), nullable=True),
    sa.Column("domaine_prioritaire_3", sa.String(length=200), nullable=True),
    sa.Column("domaine_prioritaire_4", sa.String(length=200), nullable=True),
    sa.Column("domaine_prioritaire_5", sa.String(length=200), nullable=True),
    sa.Column("nb_membres", sa.Integer(), nullable=True),
    sa.Column("nb_femmes_membres", sa.Integer(), nullable=True),
    sa.Column("nb_hommes_membres", sa.Integer(), nullable=True),
    sa.Column("nb_membres_jeunes", sa.Integer(), nullable=True),
    sa.Column("nb_membres_handicap", sa.Integer(), nullable=True),
    sa.Column("nb_membres_be", sa.Integer(), nullable=True),
    sa.Column("nombre_mandats_be", sa.Integer(), nullable=True),
    sa.Column("duree_mandat_be", sa.String(length=100), nullable=True),
    sa.Column("nb_beneficiaires", sa.Integer(), nullable=True),
    sa.Column("nb_femmes_beneficiaires", sa.Integer(), nullable=True),
    sa.Column("nb_jeunes_beneficiaires", sa.Integer(), nullable=True),
    sa.Column("nb_beneficiaires_handicap", sa.Integer(), nullable=True),
    sa.Column("adhesion_crasc_statut", sa.String(length=20), nullable=True),
    sa.Column("organes_gouvernance", sa.Text(), nullable=True),
    sa.Column("pays_couverture", sa.Text(), nullable=True),
    sa.Column("nb_personnes_engagees", sa.Integer(), nullable=True),
    sa.Column("nb_cdi", sa.Integer(), nullable=True),
    sa.Column("nb_cdd", sa.Integer(), nullable=True),
    sa.Column("date_designation_responsable", sa.String(length=30), nullable=True),
    sa.Column("date_prochaine_designation", sa.String(length=30), nullable=True),
    sa.Column("manuel_procedures", sa.Boolean(), nullable=True),
    sa.Column("plan_action_annee_cours", sa.Boolean(), nullable=True),
    sa.Column("plan_action_annee_cours_details", sa.Text(), nullable=True),
    sa.Column("plan_action", sa.Boolean(), nullable=True),
    sa.Column("nb_activites", sa.Integer(), nullable=True),
    sa.Column("date_derniere_activite", sa.String(length=30), nullable=True),
    sa.Column("rapports_annuels", sa.Boolean(), nullable=True),
    sa.Column("recommandations", sa.Text(), nullable=True),
    sa.Column("recommandations_2", sa.Text(), nullable=True),
]


def upgrade() -> None:
    with op.batch_alter_table("osc") as batch_op:
        for column in OSC_COLUMNS:
            batch_op.add_column(column)

    with op.batch_alter_table("demande_adhesion") as batch_op:
        for column in DEMANDE_COLUMNS:
            batch_op.add_column(column)


def downgrade() -> None:
    with op.batch_alter_table("demande_adhesion") as batch_op:
        for column in reversed(DEMANDE_COLUMNS):
            batch_op.drop_column(column.name)

    with op.batch_alter_table("osc") as batch_op:
        for column in reversed(OSC_COLUMNS):
            batch_op.drop_column(column.name)
