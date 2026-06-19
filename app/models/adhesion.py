# models/adhesion.py
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, String, DateTime, TEXT, func
from typing import Optional


class DemandeAdhesion(SQLModel, table=True):
    __tablename__ = "demande_adhesion"

    id: Optional[int] = Field(default=None, primary_key=True)
    nom_organisation: str = Field(max_length=200, nullable=False)
    sigle: Optional[str] = Field(default=None, max_length=100, nullable=True)
    type_organisation: str = Field(max_length=100, nullable=False)
    crasc_nom: Optional[str] = Field(default=None, max_length=200, nullable=True)
    type_osc: Optional[str] = Field(default=None, max_length=100, nullable=True)
    region: str = Field(max_length=100, nullable=False)
    departement: Optional[str] = Field(default=None, max_length=150, nullable=True)
    sous_prefecture: Optional[str] = Field(default=None, max_length=150, nullable=True)
    ville: Optional[str] = Field(default=None, max_length=100, nullable=True)
    origine_organisation: Optional[str] = Field(default=None, max_length=50, nullable=True)
    email: str = Field(max_length=200, nullable=False)
    telephone: str = Field(max_length=50, nullable=False)
    description: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True))
    motivation: str = Field(sa_column=Column(TEXT, nullable=False))
    type_document_formalisation: Optional[str] = Field(default=None, max_length=50, nullable=True)
    document_formalisation_path: Optional[str] = Field(default=None, max_length=2048, nullable=True)
    existence_siege: Optional[bool] = Field(default=None, nullable=True)
    categorie: Optional[str] = Field(default=None, max_length=100, nullable=True)
    niveau_regroupement: Optional[str] = Field(default=None, max_length=30, nullable=True)
    domaine_prioritaire: Optional[str] = Field(default=None, max_length=200, nullable=True)
    domaine_prioritaire_2: Optional[str] = Field(default=None, max_length=200, nullable=True)
    domaine_prioritaire_3: Optional[str] = Field(default=None, max_length=200, nullable=True)
    domaine_prioritaire_4: Optional[str] = Field(default=None, max_length=200, nullable=True)
    domaine_prioritaire_5: Optional[str] = Field(default=None, max_length=200, nullable=True)
    nb_membres: Optional[int] = Field(default=None, nullable=True)
    nb_femmes_membres: Optional[int] = Field(default=None, nullable=True)
    nb_hommes_membres: Optional[int] = Field(default=None, nullable=True)
    nb_membres_jeunes: Optional[int] = Field(default=None, nullable=True)
    nb_membres_handicap: Optional[int] = Field(default=None, nullable=True)
    nb_membres_be: Optional[int] = Field(default=None, nullable=True)
    nombre_mandats_be: Optional[int] = Field(default=None, nullable=True)
    duree_mandat_be: Optional[str] = Field(default=None, max_length=100, nullable=True)
    nb_beneficiaires: Optional[int] = Field(default=None, nullable=True)
    nb_femmes_beneficiaires: Optional[int] = Field(default=None, nullable=True)
    nb_jeunes_beneficiaires: Optional[int] = Field(default=None, nullable=True)
    nb_beneficiaires_handicap: Optional[int] = Field(default=None, nullable=True)
    adhesion_crasc_statut: Optional[str] = Field(default=None, max_length=20, nullable=True)
    organes_gouvernance: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True))
    pays_couverture: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True))
    nb_personnes_engagees: Optional[int] = Field(default=None, nullable=True)
    nb_cdi: Optional[int] = Field(default=None, nullable=True)
    nb_cdd: Optional[int] = Field(default=None, nullable=True)
    date_designation_responsable: Optional[str] = Field(default=None, max_length=30, nullable=True)
    date_prochaine_designation: Optional[str] = Field(default=None, max_length=30, nullable=True)
    manuel_procedures: Optional[bool] = Field(default=None, nullable=True)
    plan_action_annee_cours: Optional[bool] = Field(default=None, nullable=True)
    plan_action_annee_cours_details: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True))
    plan_action: Optional[bool] = Field(default=None, nullable=True)
    plan_action_document_path: Optional[str] = Field(default=None, max_length=2048, nullable=True)
    nb_activites: Optional[int] = Field(default=None, nullable=True)
    date_derniere_activite: Optional[str] = Field(default=None, max_length=30, nullable=True)
    rapports_annuels: Optional[bool] = Field(default=None, nullable=True)
    rapports_annuels_document_path: Optional[str] = Field(default=None, max_length=2048, nullable=True)
    adhesion_crasc_document_path: Optional[str] = Field(default=None, max_length=2048, nullable=True)
    recommandations: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True))
    recommandations_2: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True))
    statut: str = Field(default="en_attente", max_length=20, nullable=False)  # en_attente | approuvee | rejetee
    note_admin: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), server_onupdate=func.now()),
    )

    def __repr__(self) -> str:
        return f"<DemandeAdhesion: {self.nom_organisation}>"
