# schemas/adhesion.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class DemandeAdhesionCreate(BaseModel):
    nom_organisation: str
    sigle: Optional[str] = None
    type_organisation: str
    crasc_nom: Optional[str] = None
    type_osc: Optional[str] = None
    region: str
    departement: Optional[str] = None
    sous_prefecture: Optional[str] = None
    ville: Optional[str] = None
    origine_organisation: Optional[str] = None
    email: str
    telephone: str
    description: Optional[str] = None
    motivation: str
    type_document_formalisation: Optional[str] = None
    document_formalisation_path: Optional[str] = None
    existence_siege: Optional[bool] = None
    categorie: Optional[str] = None
    niveau_regroupement: Optional[str] = None
    domaine_prioritaire: Optional[str] = None
    domaine_prioritaire_2: Optional[str] = None
    domaine_prioritaire_3: Optional[str] = None
    domaine_prioritaire_4: Optional[str] = None
    domaine_prioritaire_5: Optional[str] = None
    nb_membres: Optional[int] = None
    nb_femmes_membres: Optional[int] = None
    nb_hommes_membres: Optional[int] = None
    nb_membres_jeunes: Optional[int] = None
    nb_membres_handicap: Optional[int] = None
    nb_membres_be: Optional[int] = None
    nombre_mandats_be: Optional[int] = None
    duree_mandat_be: Optional[str] = None
    nb_beneficiaires: Optional[int] = None
    nb_femmes_beneficiaires: Optional[int] = None
    nb_jeunes_beneficiaires: Optional[int] = None
    nb_beneficiaires_handicap: Optional[int] = None
    adhesion_crasc_statut: Optional[str] = None
    organes_gouvernance: Optional[str] = None
    pays_couverture: Optional[str] = None
    nb_personnes_engagees: Optional[int] = None
    nb_cdi: Optional[int] = None
    nb_cdd: Optional[int] = None
    date_designation_responsable: Optional[str] = None
    date_prochaine_designation: Optional[str] = None
    manuel_procedures: Optional[bool] = None
    plan_action_annee_cours: Optional[bool] = None
    plan_action_annee_cours_details: Optional[str] = None
    plan_action: Optional[bool] = None
    plan_action_document_path: Optional[str] = None
    nb_activites: Optional[int] = None
    date_derniere_activite: Optional[str] = None
    rapports_annuels: Optional[bool] = None
    rapports_annuels_document_path: Optional[str] = None
    adhesion_crasc_document_path: Optional[str] = None
    recommandations: Optional[str] = None
    recommandations_2: Optional[str] = None


class DemandeAdhesionRead(BaseModel):
    id: int
    nom_organisation: str
    sigle: Optional[str] = None
    type_organisation: str
    crasc_nom: Optional[str] = None
    type_osc: Optional[str] = None
    region: str
    departement: Optional[str] = None
    sous_prefecture: Optional[str] = None
    ville: Optional[str] = None
    origine_organisation: Optional[str] = None
    email: str
    telephone: str
    description: Optional[str] = None
    motivation: str
    type_document_formalisation: Optional[str] = None
    document_formalisation_path: Optional[str] = None
    existence_siege: Optional[bool] = None
    categorie: Optional[str] = None
    niveau_regroupement: Optional[str] = None
    domaine_prioritaire: Optional[str] = None
    domaine_prioritaire_2: Optional[str] = None
    domaine_prioritaire_3: Optional[str] = None
    domaine_prioritaire_4: Optional[str] = None
    domaine_prioritaire_5: Optional[str] = None
    nb_membres: Optional[int] = None
    nb_femmes_membres: Optional[int] = None
    nb_hommes_membres: Optional[int] = None
    nb_membres_jeunes: Optional[int] = None
    nb_membres_handicap: Optional[int] = None
    nb_membres_be: Optional[int] = None
    nombre_mandats_be: Optional[int] = None
    duree_mandat_be: Optional[str] = None
    nb_beneficiaires: Optional[int] = None
    nb_femmes_beneficiaires: Optional[int] = None
    nb_jeunes_beneficiaires: Optional[int] = None
    nb_beneficiaires_handicap: Optional[int] = None
    adhesion_crasc_statut: Optional[str] = None
    organes_gouvernance: Optional[str] = None
    pays_couverture: Optional[str] = None
    nb_personnes_engagees: Optional[int] = None
    nb_cdi: Optional[int] = None
    nb_cdd: Optional[int] = None
    date_designation_responsable: Optional[str] = None
    date_prochaine_designation: Optional[str] = None
    manuel_procedures: Optional[bool] = None
    plan_action_annee_cours: Optional[bool] = None
    plan_action_annee_cours_details: Optional[str] = None
    plan_action: Optional[bool] = None
    plan_action_document_path: Optional[str] = None
    nb_activites: Optional[int] = None
    date_derniere_activite: Optional[str] = None
    rapports_annuels: Optional[bool] = None
    rapports_annuels_document_path: Optional[str] = None
    adhesion_crasc_document_path: Optional[str] = None
    recommandations: Optional[str] = None
    recommandations_2: Optional[str] = None
    statut: str
    note_admin: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DemandeAdhesionUpdate(BaseModel):
    statut: Optional[str] = None
    note_admin: Optional[str] = None


class OscCredentials(BaseModel):
    osc_id: int
    osc_name: str
    email: str
    username: str
    temp_password: str


class DemandeAdhesionReadWithCredentials(DemandeAdhesionRead):
    credentials: Optional[OscCredentials] = None
