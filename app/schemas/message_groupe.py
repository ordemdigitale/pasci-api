from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CriteresDestinataires(BaseModel):
    """Sélection des destinataires d'un message groupé.

    Les critères portant sur les OSC se combinent entre eux (ET) : « CRASC Nord »
    + « Organisation de femmes » vise les OdF du CRASC Nord. À l'intérieur d'un
    critère, les valeurs se cumulent (OU). Les task forces visent les PTF
    membres et s'ajoutent (OU) à la sélection d'OSC.
    """

    crasc_ids: List[int] = []
    type_osc_ids: List[int] = []
    categories: List[str] = []
    regions: List[str] = []
    pole_ids: List[int] = []
    task_force_ids: List[int] = []
    # Garde-fou : viser toute la plateforme doit être explicite
    toutes_les_osc: bool = False


class DestinataireApercu(BaseModel):
    nom: str
    email: Optional[str] = None
    type: str  # osc | ptf
    a_un_compte: bool = False


class ApercuDestinataires(BaseModel):
    total: int
    avec_email: int
    avec_compte: int
    sans_email: int
    apercu: List[DestinataireApercu] = []


class MessageGroupeCreate(BaseModel):
    objet: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1)
    lien: Optional[str] = Field(default=None, max_length=500)
    criteres: CriteresDestinataires


class MessageGroupeRead(BaseModel):
    id: int
    objet: str
    message: str
    criteres: Optional[str] = None
    lien: Optional[str] = None
    nb_destinataires: int
    nb_emails: int
    nb_notifications: int
    auteur_id: Optional[UUID] = None
    auteur_nom: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class OptionCritere(BaseModel):
    valeur: str
    libelle: str
    nombre: Optional[int] = None


class CriteresDisponibles(BaseModel):
    """Valeurs proposées dans l'écran d'envoi, avec le nombre d'OSC concernées."""

    crasc: List[OptionCritere] = []
    types_osc: List[OptionCritere] = []
    categories: List[OptionCritere] = []
    regions: List[OptionCritere] = []
    poles: List[OptionCritere] = []
    task_forces: List[OptionCritere] = []
