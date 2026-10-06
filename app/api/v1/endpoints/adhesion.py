# api/v1/endpoints/adhesion.py
import logging
import secrets
import string
import slugify as python_slugify

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func
from sqlmodel import select, desc
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Optional

from app.database.session import get_db
from app.models.adhesion import DemandeAdhesion
from app.models.crasc import Osc, Crasc
from app.models.users import User
from app.core.auth import get_current_staff_user
from app.services.email import send_welcome_osc
from app.services.rattachement import rattacher_osc as _rattacher_osc
from app.services.file_uploads import save_formalisation_file, save_supporting_document
from app.schemas.adhesion import (
    DemandeAdhesionCreate,
    DemandeAdhesionRead,
    DemandeAdhesionUpdate,
    DemandeAdhesionReadWithCredentials,
    OscCredentials,
)

logger = logging.getLogger(__name__)

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


def _normaliser_nom(nom: Optional[str]) -> str:
    """
    Clé de comparaison des noms d'organisation.

    Les noms saisis dans les demandes diffèrent souvent de ceux déjà en base
    par la casse ou des espaces en trop ("Entente et Développement " vs
    "Entente et Développement"). Sans cette normalisation, le rattrapage
    crée une deuxième fiche pour une OSC déjà présente dans l'annuaire.
    """
    return (nom or "").strip().lower()


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
        # .strip() : plusieurs demandes ont des espaces en fin de nom, qui se
        # retrouvaient tels quels dans l'annuaire
        "name": (demande.nom_organisation or "").strip(),
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
        "axe": demande.axe,
        "specialites": demande.specialites,
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
        # L'approbation de la demande d'adhésion EST l'acte de modération :
        # l'OSC est publiée immédiatement, sans repasser par /admin/moderation.
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
    # Comparaison insensible à la casse et aux espaces : évite de créer un
    # doublon d'une OSC déjà présente dans l'annuaire. .first() et non
    # scalar_one_or_none() car la base contient déjà des noms en double.
    osc_result = await db.execute(
        select(Osc)
        .where(func.lower(func.btrim(Osc.name)) == _normaliser_nom(demande.nom_organisation))
        .order_by(Osc.id)
    )
    osc = osc_result.scalars().first()

    osc_payload = _osc_payload_from_demande(demande, crasc_id)
    if not osc:
        osc = Osc(**osc_payload)
        # Le slug est généré depuis le nom : s'assurer qu'il reste unique
        # (deux noms différents peuvent produire le même slug).
        base_slug = osc.slug or python_slugify.slugify(demande.nom_organisation)[:95]
        slug = base_slug
        counter = 1
        while True:
            existing_slug = await db.execute(select(Osc).where(Osc.slug == slug))
            if not existing_slug.scalars().first():
                break
            slug = f"{base_slug}-{counter}"
            counter += 1
        osc.slug = slug
        db.add(osc)
        await db.flush()  # obtenir l'id sans commit
    else:
        for key, value in osc_payload.items():
            if key == "name":
                continue
            if value is not None:
                setattr(osc, key, value)

    # --- 2bis. Pôle (1er domaine prioritaire), type et région ---
    # Sans ce rattachement, l'OSC validée n'apparaît dans aucun pôle de
    # concertation et échappe aux filtres par type / région.
    await _rattacher_osc(db, osc, demande.type_osc or demande.type_organisation)

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


async def _envoyer_identifiants(credentials: Optional[OscCredentials]) -> None:
    """
    Envoie par email le lien de connexion, l'identifiant et le mot de passe
    temporaire à l'OSC qui vient d'être validée.

    Uniquement pour un compte nouvellement créé : un compte existant garde
    son mot de passe, il n'y a rien à lui transmettre. Un échec d'envoi ne
    doit pas annuler l'approbation (les identifiants restent affichés à
    l'administrateur).
    """
    if not credentials or credentials.temp_password.startswith("(compte existant"):
        return
    try:
        await send_welcome_osc(
            user_name=credentials.osc_name,
            user_email=credentials.email,
            osc_name=credentials.osc_name,
            token="",
            username=credentials.email,
            password=credentials.temp_password,
        )
    except Exception:
        logger.exception("Envoi des identifiants échoué pour l'OSC %s", credentials.osc_id)


@adhesion_router.post("",response_model=DemandeAdhesionRead, status_code=status.HTTP_201_CREATED)
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


@adhesion_router.get("/admin/sans-osc", response_model=List[DemandeAdhesionRead], status_code=status.HTTP_200_OK)
async def get_demandes_sans_osc(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """
    Demandes approuvées dont l'OSC n'a jamais été créée.

    Cas laissé par l'ancien bug de provisionnement : la demande passait
    "approuvee" mais l'exception était avalée, donc ni OSC ni compte
    utilisateur. Ces demandes doivent être re-provisionnées.
    """
    query = select(DemandeAdhesion).where(DemandeAdhesion.statut == "approuvee")

    # Admin CRASC : limité à son propre CRASC
    if not current_user.is_superuser and current_user.crasc_id:
        crasc_result = await db.execute(select(Crasc).where(Crasc.id == current_user.crasc_id))
        crasc = crasc_result.scalar_one_or_none()
        if crasc:
            query = query.where(DemandeAdhesion.crasc_nom.ilike(f"%{crasc.name}%"))

    demandes = (
        await db.execute(query.order_by(desc(DemandeAdhesion.created_at)))
    ).scalars().all()
    if not demandes:
        return []

    # Même comparaison normalisée que le provisionnement, sinon la liste
    # annonce des demandes qui ne feront en réalité que republier une OSC
    # déjà présente dans l'annuaire.
    noms = [_normaliser_nom(demande.nom_organisation) for demande in demandes]
    noms_existants = {
        _normaliser_nom(nom)
        for nom in (
            await db.execute(
                select(Osc.name).where(func.lower(func.btrim(Osc.name)).in_(noms))
            )
        ).scalars().all()
    }
    return [d for d in demandes if _normaliser_nom(d.nom_organisation) not in noms_existants]


@adhesion_router.post("/admin/rattrapage-rattachements", status_code=status.HTTP_200_OK)
async def rattrapage_rattachements(
    simulation: bool = Query(True, description="True : calcule sans rien enregistrer"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """
    Rattache les OSC existantes à leur pôle (1er domaine prioritaire), leur
    type et leur région, quand ces informations manquent.

    Rattrapage des OSC créées avant que la validation ne fasse ce rattachement.
    Le type est repris de la demande d'adhésion de même nom. Superadmin
    uniquement. Par défaut en simulation : relancer avec simulation=false
    pour enregistrer.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Réservé au superadmin.")

    demandes = (await db.execute(select(DemandeAdhesion))).scalars().all()
    type_par_nom = {
        _normaliser_nom(d.nom_organisation): (d.type_osc or d.type_organisation)
        for d in demandes
        if d.type_osc or d.type_organisation
    }

    oscs = (await db.execute(select(Osc).order_by(Osc.id))).scalars().all()
    details = []
    for osc in oscs:
        rattache = await _rattacher_osc(db, osc, type_par_nom.get(_normaliser_nom(osc.name)))
        if rattache:
            details.append({"osc_id": osc.id, "osc": osc.name, **rattache})

    if simulation:
        await db.rollback()
    else:
        await db.commit()

    return {
        "simulation": simulation,
        "oscs_examinees": len(oscs),
        "oscs_rattachees": len(details),
        "poles": sum(1 for d in details if "pole" in d),
        "types": sum(1 for d in details if "type" in d),
        "regions": sum(1 for d in details if "region" in d),
        "details": details,
    }


@adhesion_router.post("/{demande_id}/provisionner",response_model=OscCredentials, status_code=status.HTTP_200_OK)
async def provisionner_demande(
    demande_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """
    (Re)crée l'OSC et le compte utilisateur d'une demande déjà approuvée.

    Sert au rattrapage des demandes approuvées restées sans OSC. Si l'OSC
    existe déjà, elle est mise à jour et publiée.
    """
    result = await db.execute(select(DemandeAdhesion).where(DemandeAdhesion.id == demande_id))
    demande = result.scalar_one_or_none()
    if not demande:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demande non trouvée.")
    if demande.statut != "approuvee":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seule une demande approuvée peut être provisionnée.",
        )

    try:
        credentials = await _provision_osc_and_user(
            demande,
            db,
            force_crasc_id=None if current_user.is_superuser else current_user.crasc_id,
        )
    except Exception as e:
        logger.exception("Provisionnement OSC échoué pour la demande %s", demande_id)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Impossible de créer l'OSC : {e}",
        )
    await _envoyer_identifiants(credentials)
    return credentials


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
            credentials = await _provision_osc_and_user(
                demande,
                db,
                force_crasc_id=None if current_user.is_superuser else current_user.crasc_id,
            )
        except Exception as e:
            # La création de l'OSC a échoué : ne pas laisser la demande "approuvée"
            # sans OSC visible — on remet le statut précédent et on remonte l'erreur.
            logger.exception("Provisionnement OSC échoué pour la demande %s", demande_id)
            await db.rollback()
            await db.refresh(demande)
            demande.statut = previous_statut
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Impossible de créer l'OSC : {e}. La demande n'a pas été approuvée.",
            )
        await _envoyer_identifiants(credentials)

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
