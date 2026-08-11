# api/v1/endpoints/adhesion.py
import secrets
import string
import slugify as python_slugify

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlmodel import select, desc
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Optional

from app.database.session import get_db
from app.models.adhesion import DemandeAdhesion
from app.models.crasc import Osc, Crasc
from app.models.users import User
from app.core.auth import get_current_staff_user
from app.services.file_uploads import save_formalisation_file, save_supporting_document
from app.schemas.adhesion import (
    DemandeAdhesionCreate,
    DemandeAdhesionRead,
    DemandeAdhesionUpdate,
    DemandeAdhesionReadWithCredentials,
    OscCredentials,
)

adhesion_router = APIRouter()

DEMANDE_DOCUMENT_UPLOADS = {
    "document_formalisation_file": (
        "document_formalisation_path",
        lambda file: save_formalisation_file(file),
    ),
    "plan_action_document_file": (
        "plan_action_document_path",
        lambda file: save_supporting_document(file, "plan_action_document_file", "osc-justificatifs/plan-action"),
    ),
    "rapports_annuels_document_file": (
        "rapports_annuels_document_path",
        lambda file: save_supporting_document(file, "rapports_annuels_document_file", "osc-justificatifs/rapports-annuels"),
    ),
    "adhesion_crasc_document_file": (
        "adhesion_crasc_document_path",
        lambda file: save_supporting_document(file, "adhesion_crasc_document_file", "osc-justificatifs/adhesion-crasc"),
    ),
}


async def _read_demande_payload(request: Request) -> DemandeAdhesionCreate:
    content_type = request.headers.get("content-type", "")
    if not content_type.startswith("multipart/form-data"):
        return DemandeAdhesionCreate(**await request.json())

    form = await request.form()
    payload = {}
    saved_documents: dict[str, str] = {}

    for key, value in form.multi_items():
        upload_config = DEMANDE_DOCUMENT_UPLOADS.get(key)
        if upload_config and hasattr(value, "filename"):
            payload_key, save_file = upload_config
            saved_path = save_file(value)
            if saved_path:
                saved_documents[payload_key] = saved_path
            continue
        if hasattr(value, "filename"):
            continue
        if value == "":
            continue
        payload[key] = value

    payload.update(saved_documents)

    return DemandeAdhesionCreate(**payload)


def _generate_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _adhesion_crasc_to_bool(statut: Optional[str]) -> Optional[bool]:
    if statut == "oui":
        return True
    if statut == "non":
        return False
    return None


def _osc_payload_from_demande(demande: DemandeAdhesion, crasc_id: Optional[int]) -> dict:
    return {
        "name": demande.nom_organisation,
        "sigle": demande.sigle,
        "description": demande.description,
        "email": demande.email,
        "phone": demande.telephone,
        "region_nom": demande.region,
        "departement": demande.departement,
        "sous_prefecture": demande.sous_prefecture,
        "ville": demande.ville,
        "origine_organisation": demande.origine_organisation,
        "crasc_id": crasc_id,
        "type_document_formalisation": demande.type_document_formalisation,
        "document_formalisation_path": demande.document_formalisation_path,
        "existence_siege": demande.existence_siege,
        "categorie": demande.categorie,
        "niveau_regroupement": demande.niveau_regroupement,
        "domaine_prioritaire": demande.domaine_prioritaire,
        "domaine_prioritaire_2": demande.domaine_prioritaire_2,
        "domaine_prioritaire_3": demande.domaine_prioritaire_3,
        "domaine_prioritaire_4": demande.domaine_prioritaire_4,
        "domaine_prioritaire_5": demande.domaine_prioritaire_5,
        "nb_membres": demande.nb_membres,
        "nb_femmes_membres": demande.nb_femmes_membres,
        "nb_hommes_membres": demande.nb_hommes_membres,
        "nb_membres_jeunes": demande.nb_membres_jeunes,
        "nb_membres_handicap": demande.nb_membres_handicap,
        "nb_membres_be": demande.nb_membres_be,
        "nombre_mandats_be": demande.nombre_mandats_be,
        "duree_mandat_be": demande.duree_mandat_be,
        "nb_beneficiaires": demande.nb_beneficiaires,
        "nb_femmes_beneficiaires": demande.nb_femmes_beneficiaires,
        "nb_jeunes_beneficiaires": demande.nb_jeunes_beneficiaires,
        "nb_beneficiaires_handicap": demande.nb_beneficiaires_handicap,
        "adhesion_crasc": _adhesion_crasc_to_bool(demande.adhesion_crasc_statut),
        "adhesion_crasc_statut": demande.adhesion_crasc_statut,
        "organes_gouvernance": demande.organes_gouvernance,
        "pays_couverture": demande.pays_couverture,
        "nb_personnes_engagees": demande.nb_personnes_engagees,
        "nb_cdi": demande.nb_cdi,
        "nb_cdd": demande.nb_cdd,
        "date_designation_responsable": demande.date_designation_responsable,
        "date_prochaine_designation": demande.date_prochaine_designation,
        "manuel_procedures": demande.manuel_procedures,
        "plan_action_annee_cours": demande.plan_action_annee_cours,
        "plan_action_annee_cours_details": demande.plan_action_annee_cours_details,
        "plan_action": demande.plan_action,
        "plan_action_document_path": demande.plan_action_document_path,
        "nb_activites": demande.nb_activites,
        "date_derniere_activite": demande.date_derniere_activite,
        "rapports_annuels": demande.rapports_annuels,
        "rapports_annuels_document_path": demande.rapports_annuels_document_path,
        "adhesion_crasc_document_path": demande.adhesion_crasc_document_path,
        "recommandations": demande.recommandations,
        "recommandations_2": demande.recommandations_2,
        "statut_publication": "publie",
    }


async def _provision_osc_and_user(
    demande: DemandeAdhesion,
    db: AsyncSession,
    force_crasc_id: Optional[int] = None,
) -> Optional[OscCredentials]:
    """
    Crée (ou retrouve) l'OSC correspondant à la demande, puis crée
    (ou met à jour) le compte utilisateur lié.
    Retourne les credentials à afficher à l'administrateur.
    """
    # --- 1. Trouver le CRASC ---
    crasc_id: Optional[int] = force_crasc_id  # Admin CRASC force son propre CRASC
    if not crasc_id and demande.crasc_nom:
        crasc_result = await db.execute(
            select(Crasc).where(Crasc.name.ilike(f"%{demande.crasc_nom}%"))
        )
        crasc = crasc_result.scalar_one_or_none()
        if crasc:
            crasc_id = crasc.id

    # --- 2. Créer ou retrouver l'OSC ---
    osc_result = await db.execute(
        select(Osc).where(Osc.name == demande.nom_organisation)
    )
    osc = osc_result.scalar_one_or_none()

    osc_payload = _osc_payload_from_demande(demande, crasc_id)
    if not osc:
        osc = Osc(**osc_payload)
        db.add(osc)
        await db.flush()  # obtenir l'id sans commit
    else:
        for key, value in osc_payload.items():
            if key == "name":
                continue
            if value is not None:
                setattr(osc, key, value)

    # --- 3. Créer ou mettre à jour l'utilisateur ---
    user_result = await db.execute(
        select(User).where(User.email == demande.email)
    )
    user = user_result.scalar_one_or_none()

    temp_password = _generate_password()
    base_username = python_slugify.slugify(demande.nom_organisation)[:30]

    if user:
        # Lier l'utilisateur existant à l'OSC
        user.osc_id = osc.id
        credentials = OscCredentials(
            osc_id=osc.id,
            osc_name=osc.name,
            email=user.email,
            username=user.username or user.email,
            temp_password="(compte existant — mot de passe inchangé)",
        )
    else:
        # S'assurer que le username est unique
        username = base_username
        counter = 1
        while True:
            existing = await db.execute(select(User).where(User.username == username))
            if not existing.scalar_one_or_none():
                break
            username = f"{base_username}-{counter}"
            counter += 1

        user = User(
            email=demande.email,
            username=username,
            is_active=True,
            is_staff=False,
            is_superuser=False,
            is_redacteur=False,
            osc_id=osc.id,
        )
        user.set_password(temp_password)
        db.add(user)

        credentials = OscCredentials(
            osc_id=osc.id,
            osc_name=osc.name,
            email=demande.email,
            username=username,
            temp_password=temp_password,
        )

    await db.commit()
    await db.refresh(osc)
    return credentials


@adhesion_router.post("", response_model=DemandeAdhesionRead, status_code=status.HTTP_201_CREATED)
async def create_demande(request: Request, db: AsyncSession = Depends(get_db)):
    """Soumettre une nouvelle demande d'adhésion"""
    try:
        data = await _read_demande_payload(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Données invalides : {e}",
        )
    demande = DemandeAdhesion(**data.model_dump())
    db.add(demande)
    await db.commit()
    await db.refresh(demande)
    return demande


@adhesion_router.get("", response_model=List[DemandeAdhesionRead], status_code=status.HTTP_200_OK)
async def get_demandes(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    statut: Optional[str] = Query(None, description="Filtrer par statut: en_attente, approuvee, rejetee"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Lister toutes les demandes d'adhésion (staff only)"""
    query = select(DemandeAdhesion).order_by(desc(DemandeAdhesion.created_at))

    # Admin CRASC : filtrer par son CRASC via le nom
    if not current_user.is_superuser and current_user.crasc_id:
        crasc_result = await db.execute(select(Crasc).where(Crasc.id == current_user.crasc_id))
        crasc = crasc_result.scalar_one_or_none()
        if crasc:
            query = query.where(DemandeAdhesion.crasc_nom.ilike(f"%{crasc.name}%"))

    if statut:
        query = query.where(DemandeAdhesion.statut == statut)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@adhesion_router.get("/{demande_id}", response_model=DemandeAdhesionRead, status_code=status.HTTP_200_OK)
async def get_demande(demande_id: int, db: AsyncSession = Depends(get_db)):
    """Obtenir une demande d'adhésion par ID"""
    result = await db.execute(select(DemandeAdhesion).where(DemandeAdhesion.id == demande_id))
    demande = result.scalar_one_or_none()
    if not demande:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demande non trouvée.")
    return demande


@adhesion_router.patch("/{demande_id}", response_model=DemandeAdhesionReadWithCredentials, status_code=status.HTTP_200_OK)
async def update_demande(
    demande_id: int,
    data: DemandeAdhesionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """
    Mettre à jour le statut d'une demande (approuver / rejeter).
    Lors de l'approbation, crée automatiquement l'OSC et le compte utilisateur associé.
    """
    result = await db.execute(select(DemandeAdhesion).where(DemandeAdhesion.id == demande_id))
    demande = result.scalar_one_or_none()
    if not demande:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demande non trouvée.")

    previous_statut = demande.statut
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(demande, key, value)
    await db.commit()
    await db.refresh(demande)

    # Provisionner OSC + utilisateur uniquement lors du passage à "approuvee"
    credentials: Optional[OscCredentials] = None
    if demande.statut == "approuvee" and previous_statut != "approuvee":
        try:
            # Admin CRASC : forcer son propre CRASC
            if not current_user.is_superuser and current_user.crasc_id:
                demande.crasc_id_override = current_user.crasc_id  # transmis à _provision_osc_and_user
            credentials = await _provision_osc_and_user(demande, db, force_crasc_id=current_user.crasc_id if not current_user.is_superuser else None)
        except Exception as e:
            # Ne pas bloquer l'approbation si la création échoue
            import traceback
            traceback.print_exc()

    response_data = demande.__dict__.copy()
    response_data["credentials"] = credentials
    return DemandeAdhesionReadWithCredentials(**{
        k: v for k, v in response_data.items() if not k.startswith("_")
    })


@adhesion_router.delete("/{demande_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_demande(
    demande_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Supprimer une demande d'adhésion"""
    result = await db.execute(select(DemandeAdhesion).where(DemandeAdhesion.id == demande_id))
    demande = result.scalar_one_or_none()
    if not demande:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demande non trouvée.")
    await db.delete(demande)
    await db.commit()
