# app/api/v1/endpoints/forum.py | Forum endpoints
import json
import os, uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form, Request
from sqlmodel import select, desc, func
from sqlalchemy import or_, text, update as sa_update, delete as sa_delete, insert as sa_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import List, Optional, Union
import slugify as slugify_lib
import time

from app.core.config import settings
from app.database.session import get_db
from app.models.forum import (
    PoleConcertation,
    TaskForceOsc,
    TaskForceMembre,
    TaskForceDocument,
    task_force_osc_membre,
    PoleSondage,
    PoleSondageOption,
    PoleSondageVote,
    ForumSujet,
    ForumCommentaire,
    ForumPieceJointe,
)
from app.models.adhesion import DemandeAdhesion
from app.models.crasc import Crasc, Osc, osc_pole_link
from app.models.users import User
from app.services.rattachement import normaliser, vider_cache
from app.services.journal import journaliser
from app.services.file_uploads import save_supporting_document
from app.services.task_force import (
    arborescence as arborescence_task_force,
    categorie_valide,
    sous_categorie_valide,
)
from app.models.slug import generer_slug
from app.services import forum_medias
from app.services.forum_synthese import brouillon as brouillon_synthese, mots_cles
from app.schemas.forum import (
    PoleConcertationCreate, PoleConcertationRead, PoleConcertationUpdate,
    PoleSondageCreate, PoleSondageRead, PoleSondageUpdate, PoleSondageVoteCreate,
    PoleSondageOptionRead, PoleMembreRead, PoleFusionRequest,
    ForumSujetCreate, ForumSujetRead, ForumSujetUpdate, ForumSujetDetail,
    ForumCommentaireCreate, ForumCommentaireRead,
    PieceJointeRead, SyntheseUpdate, ContributionRead, ContributionsSujetRead,
    TaskForceOscCreate, TaskForceOscMembre, TaskForceOscRead, TaskForceOscUpdate,
    TaskForceMembreCreate, TaskForceMembreRead, TaskForceMembreUpdate,
    TaskForceDocumentRead, ArborescenceCategorie,
)
from app.core.auth import get_current_user, get_current_staff_user, get_current_superuser, get_optional_current_user

ALLOWED_IMAGE_EXT = ["jpg", "jpeg", "png", "webp"]
ALLOWED_IMAGE_MIME = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024

async def _save_image(upload: UploadFile) -> str:
    """Save an uploaded image to UPLOAD_DIR and return the filename."""
    ext = (upload.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_IMAGE_EXT:
        raise HTTPException(status_code=400, detail=f"Format invalide. Formats acceptés: {ALLOWED_IMAGE_EXT}")
    if upload.content_type and upload.content_type not in ALLOWED_IMAGE_MIME:
        raise HTTPException(status_code=400, detail="Type de fichier invalide. Utilisez JPG, PNG ou WebP.")
    contents = await upload.read()
    if len(contents) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="L'image ne doit pas dépasser 5MB.")
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    filename = f"{uuid.uuid4()}.{ext}"
    path = os.path.join(settings.UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(contents)
    return filename

def _delete_image(image_path: Optional[str]):
    """Delete an image file from UPLOAD_DIR if it exists."""
    if image_path and not image_path.startswith("/images/"):
        full = os.path.join(settings.UPLOAD_DIR, image_path)
        if os.path.exists(full):
            os.remove(full)

forum_router = APIRouter()

POLE_LOAD_OPTIONS = (
    selectinload(PoleConcertation.oscs).selectinload(Osc.region),
    selectinload(PoleConcertation.oscs).selectinload(Osc.type),
    selectinload(PoleConcertation.oscs).selectinload(Osc.crasc),
)


async def _oscs_actives(db: AsyncSession, pole: PoleConcertation) -> set:
    """
    OSC membres du pôle ayant déjà lancé un sujet de discussion dans ce pôle
    (définition PdoC d'un « membre actif »).
    """
    membres_ids = {osc.id for osc in pole.oscs or []}
    if not membres_ids:
        return set()
    result = await db.execute(
        select(User.osc_id)
        .join(ForumSujet, ForumSujet.author_id == User.id)
        .where(ForumSujet.pole_id == pole.id, User.osc_id.is_not(None))
        .distinct()
    )
    return {osc_id for osc_id in result.scalars().all() if osc_id in membres_ids}
SONDAGE_LOAD_OPTIONS = (
    selectinload(PoleSondage.options).selectinload(PoleSondageOption.votes),
    selectinload(PoleSondage.votes),
    selectinload(PoleSondage.pole).selectinload(PoleConcertation.oscs),
)


def _json_list(values: List[str]) -> str:
    return json.dumps(values, ensure_ascii=False)


def _region_dedupe_key(region_name: str) -> str:
    return slugify_lib.slugify(region_name or "").casefold()


def _regions_avec_effectifs(pole: PoleConcertation) -> List[tuple]:
    """
    Régions des OSC membres avec leur nombre d'OSC, de la plus représentée à
    la moins représentée (ordre alphabétique à égalité). La première est la
    région affichée sur la carte du pôle (« Gbêkê (45) +26 »).
    """
    noms: dict = {}
    effectifs: dict = {}
    for osc in pole.oscs or []:
        region_name = ""
        if getattr(osc, "region", None):
            region_name = (osc.region.name or "").strip()
        if not region_name:
            region_name = (osc.region_nom or "").strip()

        region_key = _region_dedupe_key(region_name)
        if region_name and region_key:
            noms.setdefault(region_key, region_name)
            effectifs[region_key] = effectifs.get(region_key, 0) + 1
    ordre = sorted(effectifs, key=lambda cle: (-effectifs[cle], noms[cle].lower()))
    return [(noms[cle], effectifs[cle]) for cle in ordre]


async def _pole_response(db: AsyncSession, pole: PoleConcertation) -> PoleConcertationRead:
    count_result = await db.execute(
        select(func.count(ForumSujet.id)).where(ForumSujet.pole_id == pole.id)
    )
    osc_count = len(pole.oscs or [])
    pole_data = PoleConcertationRead.model_validate(pole)
    pole_data.sujets_count = count_result.scalar() or 0
    pole_data.nb_osc_membres = osc_count
    pole_data.nb_membres_actifs = len(await _oscs_actives(db, pole))
    regions = _regions_avec_effectifs(pole)
    pole_data.regions_influence = _json_list([nom for nom, _ in regions])
    pole_data.regions_effectifs = [{"nom": nom, "nb": nb} for nom, nb in regions]
    pole_data.experts = await _experts_du_pole(db, pole.id)
    return pole_data


async def _get_pole_by_slug(db: AsyncSession, pole_slug: str) -> Optional[PoleConcertation]:
    result = await db.execute(
        select(PoleConcertation)
        .options(*POLE_LOAD_OPTIONS)
        .where(PoleConcertation.slug == pole_slug)
    )
    return result.scalars().first()


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _is_sondage_closed(sondage: PoleSondage) -> bool:
    closes_at = _as_utc(sondage.closes_at)
    return sondage.status != "ouvert" or bool(closes_at and closes_at <= datetime.now(timezone.utc))


def _peut_animer(user: User, pole_id: Optional[int]) -> bool:
    """Staff, superuser ou expert du pôle : modère et anime ses discussions."""
    return bool(user.is_superuser or user.is_staff or user.anime_le_pole(pole_id))


async def _experts_du_pole(db: AsyncSession, pole_id: int) -> List[dict]:
    experts = (await db.execute(select(User).where(User.is_expert == True, User.is_active == True))).scalars().all()  # noqa: E712
    return [{"id": str(u.id), "nom": _nom_auteur(u)} for u in experts if u.anime_le_pole(pole_id)]


def _user_can_access_pole(user: User, pole: PoleConcertation) -> bool:
    if _peut_animer(user, pole.id):
        return True
    if not user.osc_id:
        return False
    return any(osc.id == user.osc_id for osc in (pole.oscs or []))


def _user_vote_option_id(sondage: PoleSondage, user: Optional[User]) -> Optional[int]:
    if not user:
        return None
    for vote in sondage.votes or []:
        if vote.user_id == user.id:
            return vote.option_id
    return None


def _can_show_sondage_results(
    sondage: PoleSondage,
    user: Optional[User],
    user_vote_option_id: Optional[int],
) -> bool:
    if user and (user.is_superuser or user.is_staff):
        return True
    if sondage.results_visibility == "always":
        return True
    if sondage.results_visibility == "after_vote" and user_vote_option_id is not None:
        return True
    if sondage.results_visibility == "after_close" and _is_sondage_closed(sondage):
        return True
    return False


def _sondage_response(sondage: PoleSondage, user: Optional[User] = None) -> PoleSondageRead:
    user_option_id = _user_vote_option_id(sondage, user)
    can_show_results = _can_show_sondage_results(sondage, user, user_option_id)
    total_votes = len(sondage.votes or [])

    options = []
    for option in sorted(sondage.options or [], key=lambda opt: (opt.ordre, opt.id or 0)):
        votes_count = len(option.votes or [])
        percentage = round((votes_count / total_votes) * 100, 1) if total_votes else 0
        options.append(
            PoleSondageOptionRead(
                id=option.id,
                label=option.label,
                ordre=option.ordre,
                votes_count=votes_count if can_show_results else 0,
                percentage=percentage if can_show_results else 0,
            )
        )

    return PoleSondageRead(
        id=sondage.id,
        pole_id=sondage.pole_id,
        question=sondage.question,
        description=sondage.description,
        status="ferme" if _is_sondage_closed(sondage) else sondage.status,
        results_visibility=sondage.results_visibility,
        closes_at=sondage.closes_at,
        created_at=sondage.created_at,
        total_votes=total_votes if can_show_results else 0,
        user_vote_option_id=user_option_id,
        can_show_results=can_show_results,
        options=options,
    )


async def _get_sondage_by_id(db: AsyncSession, sondage_id: int) -> Optional[PoleSondage]:
    result = await db.execute(
        select(PoleSondage)
        .options(*SONDAGE_LOAD_OPTIONS)
        .where(PoleSondage.id == sondage_id)
    )
    return result.scalars().first()


# ─────────────────────────────────────────────────────
# TASK FORCES (groupes d'OSC de l'espace collaboratif)
# ─────────────────────────────────────────────────────

async def _membres_task_force(db: AsyncSession, task_force_id: int) -> List[TaskForceOscMembre]:
    """OSC membres d'une task force, lues via la table de liaison.

    Lecture explicite plutôt qu'une relation : en session asynchrone, un
    chargement paresseux déclenché hors requête lève MissingGreenlet.
    """
    result = await db.execute(
        select(Osc, task_force_osc_membre.c.chef_de_file)
        .join(task_force_osc_membre, task_force_osc_membre.c.osc_id == Osc.id)
        .where(task_force_osc_membre.c.task_force_id == task_force_id)
        .order_by(task_force_osc_membre.c.chef_de_file.desc(), Osc.name)
    )
    return [
        TaskForceOscMembre(
            id=osc.id, name=osc.name, slug=osc.slug, sigle=osc.sigle,
            region_nom=osc.region_nom, email=osc.email, chef_de_file=bool(chef),
        )
        for osc, chef in result.all()
    ]


async def _task_force_response(db: AsyncSession, tf: TaskForceOsc) -> TaskForceOscRead:
    """Task force avec ses OSC membres et le chef de file éventuel."""
    membres = await _membres_task_force(db, tf.id)
    pole_nom = None
    if tf.pole_id:
        pole = await db.get(PoleConcertation, tf.pole_id)
        pole_nom = pole.name if pole else None

    nb_personnes = (await db.execute(
        select(func.count(TaskForceMembre.id)).where(TaskForceMembre.task_force_id == tf.id)
    )).scalar_one()
    nb_documents = (await db.execute(
        select(func.count(TaskForceDocument.id)).where(TaskForceDocument.task_force_id == tf.id)
    )).scalar_one()

    return TaskForceOscRead(
        id=tf.id, nom=tf.nom, slug=tf.slug, thematique=tf.thematique, zone=tf.zone,
        description=tf.description, pole_id=tf.pole_id, pole_nom=pole_nom,
        ordre=tf.ordre, actif=tf.actif, nb_membres=len(membres),
        nb_personnes=nb_personnes, nb_documents=nb_documents,
        membres=membres, created_at=tf.created_at,
    )


async def _definir_membres(
    db: AsyncSession, task_force_id: int, osc_ids: List[int], chef_de_file_id: Optional[int]
) -> None:
    """Remplace la composition d'une task force (et désigne le chef de file)."""
    await db.execute(
        sa_delete(task_force_osc_membre).where(
            task_force_osc_membre.c.task_force_id == task_force_id
        )
    )
    ids_valides = []
    if osc_ids:
        result = await db.execute(select(Osc.id).where(Osc.id.in_(osc_ids)))
        ids_valides = list(result.scalars().all())
    if ids_valides:
        await db.execute(
            sa_insert(task_force_osc_membre),
            [
                {
                    "task_force_id": task_force_id,
                    "osc_id": osc_id,
                    "chef_de_file": osc_id == chef_de_file_id,
                }
                for osc_id in ids_valides
            ],
        )


@forum_router.get("/task-forces", response_model=List[TaskForceOscRead])
async def lister_task_forces(
    include_inactive: bool = Query(False, description="Inclure les task forces désactivées (back-office)"),
    pole_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Task forces de l'espace collaboratif, avec leurs OSC membres (public)."""
    if include_inactive and not (current_user and (current_user.is_staff or current_user.is_superuser)):
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs.")

    requete = select(TaskForceOsc).order_by(TaskForceOsc.ordre, TaskForceOsc.nom)
    if not include_inactive:
        requete = requete.where(TaskForceOsc.actif == True)  # noqa: E712
    if pole_id:
        requete = requete.where(TaskForceOsc.pole_id == pole_id)

    result = await db.execute(requete)
    return [await _task_force_response(db, tf) for tf in result.scalars().all()]


# ── Espace documentaire PdoC ─────────────────────────────────────────────

def _document_read(doc: TaskForceDocument, task_force_nom: Optional[str] = None) -> TaskForceDocumentRead:
    return TaskForceDocumentRead(
        id=doc.id, task_force_id=doc.task_force_id, task_force_nom=task_force_nom,
        categorie=doc.categorie, sous_categorie=doc.sous_categorie,
        titre=doc.titre, description=doc.description,
        fichier_url=f"{settings.API_BASE_URL}/static/{doc.fichier_path}" if doc.fichier_path else None,
        fichier_nom=doc.fichier_nom, taille_octets=doc.taille_octets,
        auteur_nom=doc.auteur_nom, created_at=doc.created_at,
    )


@forum_router.get("/task-forces/documents/arborescence", response_model=List[ArborescenceCategorie])
async def arborescence_documents(
    task_force_id: Optional[int] = Query(None, description="Compter les documents de cette task force"),
    db: AsyncSession = Depends(get_db),
):
    """Arborescence de l'espace documentaire, avec le nombre de documents déposés."""
    conditions = []
    if task_force_id:
        conditions.append(TaskForceDocument.task_force_id == task_force_id)
    result = await db.execute(
        select(TaskForceDocument.categorie, func.count(TaskForceDocument.id))
        .where(*conditions)
        .group_by(TaskForceDocument.categorie)
    )
    compteurs = dict(result.all())
    return [
        ArborescenceCategorie(
            categorie=entree["categorie"],
            sous_categories=entree["sous_categories"],
            nb_documents=compteurs.get(entree["categorie"], 0),
        )
        for entree in arborescence_task_force()
    ]


@forum_router.get("/task-forces/documents", response_model=List[TaskForceDocumentRead])
async def lister_documents(
    task_force_id: Optional[int] = Query(None),
    categorie: Optional[str] = Query(None),
    sous_categorie: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Documents déposés, du plus récent au plus ancien."""
    conditions = []
    if task_force_id:
        conditions.append(TaskForceDocument.task_force_id == task_force_id)
    if categorie:
        conditions.append(TaskForceDocument.categorie == categorie)
    if sous_categorie:
        conditions.append(TaskForceDocument.sous_categorie == sous_categorie)
    if search and search.strip():
        motif = f"%{search.strip()}%"
        conditions.append(or_(
            TaskForceDocument.titre.ilike(motif),
            TaskForceDocument.description.ilike(motif),
        ))

    result = await db.execute(
        select(TaskForceDocument, TaskForceOsc.nom)
        .join(TaskForceOsc, TaskForceOsc.id == TaskForceDocument.task_force_id, isouter=True)
        .where(*conditions)
        .order_by(desc(TaskForceDocument.created_at))
        .limit(limit)
    )
    return [_document_read(doc, nom) for doc, nom in result.all()]


@forum_router.post(
    "/task-forces/documents",
    response_model=TaskForceDocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def deposer_document(
    titre: str = Form(...),
    categorie: str = Form(...),
    sous_categorie: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    task_force_id: Optional[int] = Form(None),
    fichier: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Déposer un document dans l'espace documentaire (staff only)."""
    if not categorie_valide(categorie):
        raise HTTPException(status_code=422, detail=f"Catégorie inconnue : {categorie}")
    if not sous_categorie_valide(categorie, sous_categorie):
        raise HTTPException(
            status_code=422,
            detail=f"« {sous_categorie} » n'appartient pas à la catégorie « {categorie} ».",
        )
    if task_force_id and not await db.get(TaskForceOsc, task_force_id):
        raise HTTPException(status_code=404, detail="Task force non trouvée.")

    chemin = nom_fichier = None
    taille = None
    if fichier and fichier.filename:
        chemin = save_supporting_document(fichier, "fichier", relative_dir="task-forces")
        nom_fichier = fichier.filename[:300]
        try:
            taille = os.path.getsize(os.path.join(settings.UPLOAD_DIR, chemin))
        except OSError:
            taille = None

    doc = TaskForceDocument(
        task_force_id=task_force_id, categorie=categorie, sous_categorie=sous_categorie or None,
        titre=titre.strip(), description=(description or "").strip() or None,
        fichier_path=chemin, fichier_nom=nom_fichier, taille_octets=taille,
        auteur_id=current_user.id,
        auteur_nom=current_user.full_name or current_user.username or current_user.email,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    await journaliser(
        db, current_user, action="task_force_document_depose", cible_type="task_force",
        cible_id=str(task_force_id) if task_force_id else None, cible_libelle=doc.titre,
        details=f"{categorie}{' · ' + sous_categorie if sous_categorie else ''}",
    )
    return _document_read(doc)


@forum_router.delete("/task-forces/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def supprimer_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    doc = await db.get(TaskForceDocument, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document non trouvé.")
    titre = doc.titre
    if doc.fichier_path:
        chemin = os.path.join(settings.UPLOAD_DIR, doc.fichier_path)
        if os.path.exists(chemin):
            os.remove(chemin)
    await db.delete(doc)
    await db.commit()
    await journaliser(
        db, current_user, action="task_force_document_supprime", cible_type="task_force",
        cible_libelle=titre,
    )
    return None


@forum_router.get("/task-forces/nationale/membres", response_model=List[TaskForceMembreRead])
async def membres_task_force_nationale(db: AsyncSession = Depends(get_db)):
    """Task force nationale : composée des coordonnateurs des task forces régionales.

    Groupe virtuel — il n'est pas stocké : sa composition se déduit des membres
    marqués coordonnateur dans chaque task force active.
    """
    result = await db.execute(
        select(TaskForceMembre, TaskForceOsc.nom)
        .join(TaskForceOsc, TaskForceOsc.id == TaskForceMembre.task_force_id)
        .where(TaskForceMembre.est_coordonnateur == True, TaskForceOsc.actif == True)  # noqa: E712
        .order_by(TaskForceOsc.ordre, TaskForceOsc.nom, TaskForceMembre.ordre, TaskForceMembre.nom)
    )
    return [await _membre_read(db, membre, nom_tf) for membre, nom_tf in result.all()]


@forum_router.get("/task-forces/{slug}", response_model=TaskForceOscRead)
async def detail_task_force(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TaskForceOsc).where(TaskForceOsc.slug == slug))
    tf = result.scalars().first()
    if not tf:
        raise HTTPException(status_code=404, detail="Task force non trouvée.")
    return await _task_force_response(db, tf)


@forum_router.post("/task-forces", response_model=TaskForceOscRead, status_code=status.HTTP_201_CREATED)
async def creer_task_force(
    data: TaskForceOscCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Créer une task force et lui rattacher des OSC (staff only)."""
    existe = await db.execute(select(TaskForceOsc).where(func.lower(TaskForceOsc.nom) == data.nom.strip().lower()))
    if existe.scalars().first():
        raise HTTPException(status_code=409, detail="Une task force porte déjà ce nom.")

    tf = TaskForceOsc(
        nom=data.nom.strip(), thematique=data.thematique, zone=data.zone,
        description=data.description, pole_id=data.pole_id, ordre=data.ordre,
        actif=data.actif,
    )
    db.add(tf)
    await db.flush()
    await _definir_membres(db, tf.id, data.osc_ids, data.chef_de_file_id)
    await db.commit()
    await db.refresh(tf)

    await journaliser(
        db, current_user, action="task_force_creee", cible_type="task_force",
        cible_id=str(tf.id), cible_libelle=tf.nom,
        details=f"{len(data.osc_ids)} OSC membre(s)",
    )
    return await _task_force_response(db, tf)


@forum_router.patch("/task-forces/{task_force_id}", response_model=TaskForceOscRead)
async def modifier_task_force(
    task_force_id: int,
    data: TaskForceOscUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Modifier une task force ou la composition de ses membres (staff only)."""
    tf = await db.get(TaskForceOsc, task_force_id)
    if not tf:
        raise HTTPException(status_code=404, detail="Task force non trouvée.")

    champs = data.model_dump(exclude_unset=True, exclude={"osc_ids", "chef_de_file_id"})
    for cle, valeur in champs.items():
        setattr(tf, cle, valeur)
    if "nom" in champs and champs["nom"]:
        tf.slug = generer_slug(champs["nom"], 200)

    if data.osc_ids is not None:
        await _definir_membres(db, tf.id, data.osc_ids, data.chef_de_file_id)
    elif data.chef_de_file_id is not None:
        membres_actuels = [m.id for m in await _membres_task_force(db, tf.id)]
        await _definir_membres(db, tf.id, membres_actuels, data.chef_de_file_id)

    tf.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(tf)

    await journaliser(
        db, current_user, action="task_force_modifiee", cible_type="task_force",
        cible_id=str(tf.id), cible_libelle=tf.nom,
    )
    return await _task_force_response(db, tf)


@forum_router.delete("/task-forces/{task_force_id}", status_code=status.HTTP_204_NO_CONTENT)
async def supprimer_task_force(
    task_force_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Supprimer une task force (staff only). Les OSC membres ne sont pas touchées."""
    tf = await db.get(TaskForceOsc, task_force_id)
    if not tf:
        raise HTTPException(status_code=404, detail="Task force non trouvée.")
    nom, tf_id = tf.nom, str(tf.id)
    await db.delete(tf)
    await db.commit()
    await journaliser(
        db, current_user, action="task_force_supprimee", cible_type="task_force",
        cible_id=tf_id, cible_libelle=nom,
    )
    return None


# ── Membres d'une task force ─────────────────────────────────────────────

async def _membre_read(db: AsyncSession, membre: TaskForceMembre, task_force_nom: Optional[str] = None) -> TaskForceMembreRead:
    osc_nom = osc_slug = None
    if membre.osc_id:
        osc = await db.get(Osc, membre.osc_id)
        if osc:
            osc_nom, osc_slug = osc.name, osc.slug
    return TaskForceMembreRead(
        id=membre.id, task_force_id=membre.task_force_id, osc_id=membre.osc_id,
        titre=membre.titre, nom=membre.nom, fonction=membre.fonction,
        contact=membre.contact, email=membre.email, zone_crasc=membre.zone_crasc,
        groupes_thematiques=membre.groupes_thematiques, role=membre.role,
        est_coordonnateur=membre.est_coordonnateur, ordre=membre.ordre,
        osc_nom=osc_nom, osc_slug=osc_slug, task_force_nom=task_force_nom,
        created_at=membre.created_at,
    )


async def _zone_crasc_de_losc(db: AsyncSession, osc_id: Optional[int]) -> Optional[str]:
    """Zone CRASC déduite de l'OSC représentée."""
    if not osc_id:
        return None
    osc = await db.get(Osc, osc_id)
    if not osc or not osc.crasc_id:
        return None
    crasc = await db.get(Crasc, osc.crasc_id)
    return crasc.name if crasc else None


@forum_router.get("/task-forces/{task_force_id}/membres", response_model=List[TaskForceMembreRead])
async def lister_membres(task_force_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TaskForceMembre)
        .where(TaskForceMembre.task_force_id == task_force_id)
        .order_by(
            TaskForceMembre.est_coordonnateur.desc(), TaskForceMembre.ordre, TaskForceMembre.nom
        )
    )
    return [await _membre_read(db, m) for m in result.scalars().all()]


@forum_router.post(
    "/task-forces/{task_force_id}/membres",
    response_model=TaskForceMembreRead,
    status_code=status.HTTP_201_CREATED,
)
async def ajouter_membre(
    task_force_id: int,
    data: TaskForceMembreCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Ajouter une personne à une task force (staff only)."""
    tf = await db.get(TaskForceOsc, task_force_id)
    if not tf:
        raise HTTPException(status_code=404, detail="Task force non trouvée.")

    membre = TaskForceMembre(task_force_id=task_force_id, **data.model_dump())
    if not membre.zone_crasc:
        membre.zone_crasc = await _zone_crasc_de_losc(db, membre.osc_id)
    db.add(membre)
    await db.commit()
    await db.refresh(membre)

    await journaliser(
        db, current_user, action="task_force_membre_ajoute", cible_type="task_force",
        cible_id=str(task_force_id), cible_libelle=tf.nom,
        details=f"{membre.nom}{' (coordonnateur)' if membre.est_coordonnateur else ''}",
    )
    return await _membre_read(db, membre)


@forum_router.patch("/task-forces/membres/{membre_id}", response_model=TaskForceMembreRead)
async def modifier_membre(
    membre_id: int,
    data: TaskForceMembreUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    membre = await db.get(TaskForceMembre, membre_id)
    if not membre:
        raise HTTPException(status_code=404, detail="Membre non trouvé.")
    champs = data.model_dump(exclude_unset=True)
    for cle, valeur in champs.items():
        setattr(membre, cle, valeur)
    if "osc_id" in champs and not champs.get("zone_crasc"):
        membre.zone_crasc = await _zone_crasc_de_losc(db, membre.osc_id)
    await db.commit()
    await db.refresh(membre)
    return await _membre_read(db, membre)


@forum_router.delete("/task-forces/membres/{membre_id}", status_code=status.HTTP_204_NO_CONTENT)
async def supprimer_membre(
    membre_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    membre = await db.get(TaskForceMembre, membre_id)
    if not membre:
        raise HTTPException(status_code=404, detail="Membre non trouvé.")
    nom, tf_id = membre.nom, membre.task_force_id
    await db.delete(membre)
    await db.commit()
    await journaliser(
        db, current_user, action="task_force_membre_retire", cible_type="task_force",
        cible_id=str(tf_id), cible_libelle=nom,
    )
    return None


# ─────────────────────────────────────────────────────
# PÔLES
# ─────────────────────────────────────────────────────

@forum_router.get("/poles", response_model=List[PoleConcertationRead])
async def list_poles(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    include_inactive: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Liste tous les pôles de concertation (public)"""
    if include_inactive and not (current_user and (current_user.is_staff or current_user.is_superuser)):
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs.")

    statement = (
        select(PoleConcertation)
        .options(*POLE_LOAD_OPTIONS)
        .order_by(PoleConcertation.name)
        .offset(skip)
        .limit(limit)
    )
    if not include_inactive:
        statement = statement.where(PoleConcertation.is_active == True)

    result = await db.execute(
        statement
    )
    poles = result.scalars().all()

    return [await _pole_response(db, pole) for pole in poles]


@forum_router.post("/poles", response_model=PoleConcertationRead, status_code=status.HTTP_201_CREATED)
async def create_pole(
    name: str = Form(...),
    category: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    objectifs: Optional[str] = Form(None),
    objectifs_annuels: Optional[str] = Form(None),
    nb_osc_membres: Optional[int] = Form(None),
    regions_influence: Optional[str] = Form(None),
    realisations: Optional[str] = Form(None),
    projets_en_cours: Optional[str] = Form(None),
    agenda: Optional[str] = Form(None),
    is_active: bool = Form(True),
    image: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Créer un pôle (staff ou superuser)"""
    image_path = None
    if image and image.filename:
        image_path = await _save_image(image)

    db_pole = PoleConcertation(
        name=name,
        category=category,
        description=description,
        image_path=image_path,
        objectifs=objectifs,
        objectifs_annuels=objectifs_annuels,
        nb_osc_membres=nb_osc_membres,
        regions_influence=regions_influence,
        realisations=realisations,
        projets_en_cours=projets_en_cours,
        agenda=agenda,
        is_active=is_active,
    )
    db.add(db_pole)
    await db.commit()
    created = await _get_pole_by_slug(db, db_pole.slug)
    return await _pole_response(db, created or db_pole)


@forum_router.get("/poles/{pole_slug}", response_model=PoleConcertationRead)
async def get_pole(pole_slug: str, db: AsyncSession = Depends(get_db)):
    """Détail d'un pôle (public)"""
    pole = await _get_pole_by_slug(db, pole_slug)
    if not pole:
        raise HTTPException(status_code=404, detail="Pôle non trouvé.")
    return await _pole_response(db, pole)


@forum_router.patch("/poles/{pole_slug}", response_model=PoleConcertationRead)
async def update_pole(
    pole_slug: str,
    name: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    objectifs: Optional[str] = Form(None),
    objectifs_annuels: Optional[str] = Form(None),
    nb_osc_membres: Optional[str] = Form(None),
    regions_influence: Optional[str] = Form(None),
    realisations: Optional[str] = Form(None),
    projets_en_cours: Optional[str] = Form(None),
    agenda: Optional[str] = Form(None),
    is_active: Optional[str] = Form(None),
    remove_image: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Modifier un pôle (staff ou superuser)"""
    pole = await _get_pole_by_slug(db, pole_slug)
    if not pole:
        raise HTTPException(status_code=404, detail="Pôle non trouvé.")

    if remove_image and remove_image.lower() in ("true", "1", "yes"):
        _delete_image(pole.image_path)
        pole.image_path = None
    elif image and hasattr(image, 'filename') and image.filename:
        _delete_image(pole.image_path)
        pole.image_path = await _save_image(image)

    if name is not None and name != pole.name:
        # Le nom du pôle EST le domaine prioritaire : garder les OSC alignées
        await _renommer_domaine(db, pole.name, name)
        pole.name = name
        pole.slug = slugify_lib.slugify(name)
    if category is not None:
        pole.category = category or None
    if description is not None:
        pole.description = description or None
    if objectifs is not None:
        pole.objectifs = objectifs or None
    if objectifs_annuels is not None:
        pole.objectifs_annuels = objectifs_annuels or None
    if nb_osc_membres is not None:
        try:
            pole.nb_osc_membres = int(nb_osc_membres) if nb_osc_membres else None
        except ValueError:
            pole.nb_osc_membres = None
    if regions_influence is not None:
        pole.regions_influence = regions_influence or None
    if realisations is not None:
        pole.realisations = realisations or None
    if projets_en_cours is not None:
        pole.projets_en_cours = projets_en_cours or None
    if agenda is not None:
        pole.agenda = agenda or None
    if is_active is not None:
        pole.is_active = is_active.lower() in ("true", "1", "yes")

    await db.commit()
    updated = await _get_pole_by_slug(db, pole.slug)
    return await _pole_response(db, updated or pole)


@forum_router.delete("/poles/{pole_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pole(
    pole_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    result = await db.execute(
        select(PoleConcertation).where(PoleConcertation.slug == pole_slug)
    )
    pole = result.scalar_one_or_none()
    if not pole:
        raise HTTPException(status_code=404, detail="Pôle non trouvé.")
    _delete_image(pole.image_path)
    await db.delete(pole)
    await db.commit()
    return None


DOMAINE_COLUMNS = (
    "domaine_prioritaire",
    "domaine_prioritaire_2",
    "domaine_prioritaire_3",
    "domaine_prioritaire_4",
    "domaine_prioritaire_5",
)


async def _renommer_domaine(db: AsyncSession, ancien: str, nouveau: str) -> None:
    """
    Les pôles portent le nom des domaines prioritaires : quand un pôle est
    renommé ou fusionné, les OSC et demandes d'adhésion qui citaient l'ancien
    nom doivent pointer vers le nouveau, sinon elles ne sont plus rattachées.
    """
    # Comparaison sans accents ni casse (comme le rattachement), faite en
    # Python : la base n'a pas l'extension unaccent.
    cle_ancien = normaliser(ancien)
    if not cle_ancien:
        return
    for model in (Osc, DemandeAdhesion):
        colonnes = [getattr(model, name) for name in DOMAINE_COLUMNS]
        lignes = (await db.execute(select(model.id, *colonnes))).all()
        for ligne in lignes:
            valeurs = {
                name: nouveau
                for name, valeur in zip(DOMAINE_COLUMNS, ligne[1:])
                if valeur and normaliser(valeur) == cle_ancien
            }
            if valeurs:
                await db.execute(sa_update(model).where(model.id == ligne[0]).values(valeurs))


@forum_router.post("/poles/{pole_slug}/fusionner", response_model=PoleConcertationRead)
async def fusionner_pole(
    pole_slug: str,
    payload: PoleFusionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """
    Fusionne le pôle `pole_slug` (source) dans `cible_slug`.

    Les OSC membres, sujets de discussion et sondages de la source passent
    dans la cible ; les domaines prioritaires des OSC sont mis à jour ; la
    source est désactivée (conservée pour l'historique, plus proposée dans
    les formulaires). `nouveau_nom` renomme le pôle fusionné.
    """
    source = await _get_pole_by_slug(db, pole_slug)
    cible = await _get_pole_by_slug(db, payload.cible_slug)
    if not source or not cible:
        raise HTTPException(status_code=404, detail="Pôle non trouvé.")
    if source.id == cible.id:
        raise HTTPException(status_code=400, detail="Un pôle ne peut pas être fusionné avec lui-même.")

    nouveau_nom = (payload.nouveau_nom or "").strip() or cible.name
    if nouveau_nom != cible.name:
        conflit = await db.execute(
            select(PoleConcertation).where(
                PoleConcertation.name == nouveau_nom, PoleConcertation.id.not_in([source.id, cible.id])
            )
        )
        if conflit.scalars().first():
            raise HTTPException(status_code=409, detail="Un autre pôle porte déjà ce nom.")

    # 1. OSC membres : une OSC n'appartient qu'à un pôle, elle passe dans la cible
    membres_source = (
        await db.execute(select(osc_pole_link.c.osc_id).where(osc_pole_link.c.pole_id == source.id))
    ).scalars().all()
    await db.execute(sa_delete(osc_pole_link).where(osc_pole_link.c.pole_id == source.id))
    if membres_source:
        deja_cible = set(
            (
                await db.execute(
                    select(osc_pole_link.c.osc_id).where(
                        osc_pole_link.c.pole_id == cible.id, osc_pole_link.c.osc_id.in_(membres_source)
                    )
                )
            ).scalars().all()
        )
        nouveaux = [{"osc_id": osc_id, "pole_id": cible.id} for osc_id in membres_source if osc_id not in deja_cible]
        if nouveaux:
            await db.execute(sa_insert(osc_pole_link), nouveaux)

    # 2. Discussions et sondages
    await db.execute(sa_update(ForumSujet).where(ForumSujet.pole_id == source.id).values(pole_id=cible.id))
    await db.execute(sa_update(PoleSondage).where(PoleSondage.pole_id == source.id).values(pole_id=cible.id))

    # 3. Noms : domaines prioritaires des OSC alignés sur le pôle fusionné
    ancien_nom_cible = cible.name
    if nouveau_nom != ancien_nom_cible:
        await _renommer_domaine(db, ancien_nom_cible, nouveau_nom)
        cible.name = nouveau_nom
        cible.slug = slugify_lib.slugify(nouveau_nom)
    await _renommer_domaine(db, source.name, nouveau_nom)

    # 4. Source désactivée, pas supprimée
    source.is_active = False

    cible_slug = cible.slug
    await db.commit()
    vider_cache(db)
    # Recharger la cible : ses membres ont changé hors ORM (table osc_pole)
    db.expire_all()
    fusionne = await _get_pole_by_slug(db, cible_slug)
    return await _pole_response(db, fusionne)


@forum_router.get("/poles/{pole_slug}/membres", response_model=List[PoleMembreRead])
async def list_pole_membres(
    pole_slug: str,
    type_name: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Liste les OSC membres d'un pôle, avec filtre optionnel par type."""
    pole = await _get_pole_by_slug(db, pole_slug)
    if not pole:
        raise HTTPException(status_code=404, detail="Pôle non trouvé.")

    normalized_type = type_name.strip().lower() if type_name else None
    actives = await _oscs_actives(db, pole)
    membres = []
    for osc in sorted(pole.oscs or [], key=lambda item: (item.name or "").lower()):
        osc_type_name = osc.type.name if getattr(osc, "type", None) else None
        candidates = [
            (osc_type_name or "").strip().lower(),
            (osc.categorie or "").strip().lower(),
        ]
        if normalized_type and normalized_type not in candidates:
            continue
        thumbnail_url = None
        if osc.thumbnail_path and osc.thumbnail_path != "default.png":
            thumbnail_url = f"{settings.API_BASE_URL}/static/{osc.thumbnail_path}"
        membres.append(
            PoleMembreRead(
                id=osc.id,
                name=osc.name,
                slug=osc.slug,
                sigle=osc.sigle,
                type_id=osc.type_id,
                type_name=osc_type_name,
                categorie=osc.categorie,
                # Les OSC importées n'ont que region_id : prendre le nom de la région liée
                region_nom=(osc.region.name if getattr(osc, "region", None) else None) or osc.region_nom,
                ville=osc.ville,
                thumbnail_url=thumbnail_url,
                crasc_id=osc.crasc_id,
                crasc_nom=osc.crasc.name if getattr(osc, "crasc", None) else None,
                axe=osc.axe,
                specialites=osc.specialites,
                est_actif=osc.id in actives,
            )
        )
    return membres


# ─────────────────────────────────────────────────────
# SONDAGES / VOTES
# ─────────────────────────────────────────────────────

@forum_router.get("/poles/{pole_slug}/sondages", response_model=List[PoleSondageRead])
async def list_sondages(
    pole_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Liste les sondages d'un pôle avec les résultats visibles selon le contexte."""
    pole = await _get_pole_by_slug(db, pole_slug)
    if not pole:
        raise HTTPException(status_code=404, detail="Pôle non trouvé.")

    result = await db.execute(
        select(PoleSondage)
        .options(*SONDAGE_LOAD_OPTIONS)
        .where(PoleSondage.pole_id == pole.id)
        .order_by(desc(PoleSondage.created_at))
    )
    sondages = result.scalars().all()
    return [_sondage_response(sondage, current_user) for sondage in sondages]


@forum_router.post("/poles/{pole_slug}/sondages", response_model=PoleSondageRead, status_code=status.HTTP_201_CREATED)
async def create_sondage(
    pole_slug: str,
    payload: PoleSondageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Créer un sondage dans un pôle (superuser only)."""
    pole = await _get_pole_by_slug(db, pole_slug)
    if not pole:
        raise HTTPException(status_code=404, detail="Pôle non trouvé.")

    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="La question du sondage est obligatoire.")
    options = [option.strip() for option in payload.options if option.strip()]
    if len(options) < 2:
        raise HTTPException(status_code=400, detail="Un sondage doit contenir au moins deux choix.")

    sondage = PoleSondage(
        pole_id=pole.id,
        question=question,
        description=payload.description.strip() if payload.description else None,
        status=payload.status,
        results_visibility=payload.results_visibility,
        closes_at=payload.closes_at,
        created_by=current_user.id,
    )
    db.add(sondage)
    await db.flush()

    for index, label in enumerate(options):
        db.add(PoleSondageOption(sondage_id=sondage.id, label=label, ordre=index))

    await db.commit()
    created = await _get_sondage_by_id(db, sondage.id)
    return _sondage_response(created or sondage, current_user)


@forum_router.patch("/sondages/{sondage_id}", response_model=PoleSondageRead)
async def update_sondage(
    sondage_id: int,
    payload: PoleSondageUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Modifier les métadonnées d'un sondage (superuser only)."""
    sondage = await _get_sondage_by_id(db, sondage_id)
    if not sondage:
        raise HTTPException(status_code=404, detail="Sondage non trouvé.")

    if payload.question is not None:
        question = payload.question.strip()
        if not question:
            raise HTTPException(status_code=400, detail="La question du sondage est obligatoire.")
        sondage.question = question
    if payload.description is not None:
        sondage.description = payload.description.strip() or None
    if payload.status is not None:
        sondage.status = payload.status
    if payload.results_visibility is not None:
        sondage.results_visibility = payload.results_visibility
    if payload.closes_at is not None:
        sondage.closes_at = payload.closes_at

    await db.commit()
    updated = await _get_sondage_by_id(db, sondage_id)
    return _sondage_response(updated or sondage, current_user)


@forum_router.delete("/sondages/{sondage_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sondage(
    sondage_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    sondage = await db.get(PoleSondage, sondage_id)
    if not sondage:
        raise HTTPException(status_code=404, detail="Sondage non trouvé.")
    await db.delete(sondage)
    await db.commit()
    return None


@forum_router.post("/sondages/{sondage_id}/vote", response_model=PoleSondageRead)
async def vote_sondage(
    sondage_id: int,
    payload: PoleSondageVoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Voter pour une option. Un utilisateur ne garde qu'un vote par sondage."""
    sondage = await _get_sondage_by_id(db, sondage_id)
    if not sondage:
        raise HTTPException(status_code=404, detail="Sondage non trouvé.")
    if not sondage.pole or not _user_can_access_pole(current_user, sondage.pole):
        raise HTTPException(status_code=403, detail="Vous n'avez pas accès à ce sondage.")
    if _is_sondage_closed(sondage):
        raise HTTPException(status_code=400, detail="Ce sondage est fermé.")

    option_ids = {option.id for option in sondage.options or []}
    if payload.option_id not in option_ids:
        raise HTTPException(status_code=400, detail="Choix invalide pour ce sondage.")

    result = await db.execute(
        select(PoleSondageVote).where(
            PoleSondageVote.sondage_id == sondage.id,
            PoleSondageVote.user_id == current_user.id,
        )
    )
    vote = result.scalar_one_or_none()
    if vote:
        vote.option_id = payload.option_id
    else:
        db.add(
            PoleSondageVote(
                sondage_id=sondage.id,
                option_id=payload.option_id,
                user_id=current_user.id,
                osc_id=current_user.osc_id,
            )
        )

    await db.commit()
    updated = await _get_sondage_by_id(db, sondage.id)
    return _sondage_response(updated or sondage, current_user)


# ─────────────────────────────────────────────────────
# SUJETS
# ─────────────────────────────────────────────────────

@forum_router.get("/poles/{pole_slug}/sujets", response_model=List[ForumSujetRead])
async def list_sujets(
    pole_slug: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Liste les sujets d'un pôle (public)"""
    pole_result = await db.execute(
        select(PoleConcertation).where(PoleConcertation.slug == pole_slug)
    )
    pole = pole_result.scalars().first()
    if not pole:
        raise HTTPException(status_code=404, detail="Pôle non trouvé.")

    statement = select(ForumSujet).where(ForumSujet.pole_id == pole.id)
    if search and search.strip():
        term = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                ForumSujet.title.ilike(term),
                ForumSujet.content.ilike(term),
                ForumSujet.author_name.ilike(term),
            )
        )
    result = await db.execute(
        statement
        .order_by(desc(ForumSujet.is_pinned), desc(ForumSujet.created_at))
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


# ───────── Messages multimédias : lecture JSON ou multipart ─────────

async def _lire_message(request: Request) -> tuple:
    """
    Corps d'un sujet ou d'un message : JSON (texte seul, anciens clients) ou
    multipart/form-data (texte + fichiers « fichiers »). Retourne
    (champs texte, liste de fichiers).
    """
    content_type = request.headers.get("content-type", "")
    if content_type.startswith(("multipart/form-data", "application/x-www-form-urlencoded")):
        form = await request.form()
        champs = {k: v for k, v in form.items() if isinstance(v, str)}
        fichiers = [v for k, v in form.multi_items() if k == "fichiers" and hasattr(v, "filename")]
        return champs, fichiers
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=422, detail="Corps de requête invalide.")
    return (data if isinstance(data, dict) else {}), []


def _nom_auteur(user: User) -> str:
    return user.username or f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email


async def _pieces_par(db: AsyncSession, *, sujet_id: Optional[int] = None, commentaire_ids: Optional[List[int]] = None) -> dict:
    """Pièces jointes groupées : {"sujet": [...], commentaire_id: [...]}."""
    groupes: dict = {}
    if sujet_id is not None:
        rows = (await db.execute(
            select(ForumPieceJointe).where(ForumPieceJointe.sujet_id == sujet_id).order_by(ForumPieceJointe.id)
        )).scalars().all()
        groupes["sujet"] = [PieceJointeRead(**forum_medias.serialiser(p)) for p in rows]
    if commentaire_ids:
        rows = (await db.execute(
            select(ForumPieceJointe)
            .where(ForumPieceJointe.commentaire_id.in_(commentaire_ids))
            .order_by(ForumPieceJointe.id)
        )).scalars().all()
        for p in rows:
            groupes.setdefault(p.commentaire_id, []).append(PieceJointeRead(**forum_medias.serialiser(p)))
    return groupes


@forum_router.get("/medias/limites")
async def limites_medias():
    """Tailles maximales (Mo) des photos, audios et vidéos, et nombre de fichiers par message."""
    return forum_medias.limites_mo()


@forum_router.post("/poles/{pole_slug}/sujets", response_model=ForumSujetDetail, status_code=status.HTTP_201_CREATED)
async def create_sujet(
    pole_slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Créer un sujet dans un pôle (utilisateur connecté). JSON {title, content}
    ou multipart (title, content, fichiers) pour joindre photos, audio, vidéos.
    """
    pole_result = await db.execute(
        select(PoleConcertation).where(PoleConcertation.slug == pole_slug)
    )
    pole = pole_result.scalars().first()
    if not pole:
        raise HTTPException(status_code=404, detail="Pôle non trouvé.")

    champs, fichiers = await _lire_message(request)
    title = (champs.get("title") or "").strip()
    content = (champs.get("content") or "").strip()
    if not title:
        raise HTTPException(status_code=422, detail="Le titre est requis.")
    if not content and not fichiers:
        raise HTTPException(status_code=422, detail="Écrivez un message ou joignez un fichier.")

    pieces = await forum_medias.enregistrer_fichiers(fichiers)
    base_slug = slugify_lib.slugify(title)
    unique_slug = f"{base_slug}-{int(time.time())}"

    db_sujet = ForumSujet(
        title=title,
        slug=unique_slug,
        content=content,
        pole_id=pole.id,
        author_id=current_user.id,
        author_name=_nom_auteur(current_user),
    )
    try:
        db.add(db_sujet)
        await db.flush()
        for piece in pieces:
            piece.sujet_id = db_sujet.id
            db.add(piece)
        await db.commit()
    except Exception:
        await db.rollback()
        forum_medias.supprimer_fichiers(pieces)
        raise
    await db.refresh(db_sujet)
    groupes = await _pieces_par(db, sujet_id=db_sujet.id)
    return ForumSujetDetail(
        **ForumSujetRead.model_validate(db_sujet).model_dump(),
        commentaires=[],
        pieces_jointes=groupes.get("sujet", []),
    )


@forum_router.get("/poles/{pole_slug}/sujets/{sujet_slug}", response_model=ForumSujetDetail)
async def get_sujet(
    pole_slug: str,
    sujet_slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Détail d'un sujet avec ses commentaires (public)"""
    pole_result = await db.execute(
        select(PoleConcertation).where(PoleConcertation.slug == pole_slug)
    )
    pole = pole_result.scalars().first()
    if not pole:
        raise HTTPException(status_code=404, detail="Pôle non trouvé.")

    sujet_result = await db.execute(
        select(ForumSujet).where(
            ForumSujet.slug == sujet_slug,
            ForumSujet.pole_id == pole.id,
        )
    )
    sujet = sujet_result.scalars().first()
    if not sujet:
        raise HTTPException(status_code=404, detail="Sujet non trouvé.")

    # Increment views
    sujet.views_count += 1
    await db.commit()
    await db.refresh(sujet)

    # Load comments
    comments_result = await db.execute(
        select(ForumCommentaire)
        .where(ForumCommentaire.sujet_id == sujet.id)
        .order_by(ForumCommentaire.created_at)
    )
    commentaires = comments_result.scalars().all()
    groupes = await _pieces_par(db, sujet_id=sujet.id, commentaire_ids=[c.id for c in commentaires])

    # Build response manually to avoid SQLAlchemy lazy-load issues
    commentaires_data = [
        ForumCommentaireRead(
            id=c.id,
            content=c.content,
            sujet_id=c.sujet_id,
            author_id=c.author_id,
            author_name=c.author_name,
            created_at=c.created_at,
            updated_at=c.updated_at,
            pieces_jointes=groupes.get(c.id, []),
        )
        for c in commentaires
    ]

    return ForumSujetDetail(
        **ForumSujetRead.model_validate(sujet).model_dump(),
        commentaires=commentaires_data,
        pieces_jointes=groupes.get("sujet", []),
        experts=await _experts_du_pole(db, pole.id),
    )


@forum_router.patch("/poles/{pole_slug}/sujets/{sujet_slug}", response_model=ForumSujetRead)
async def update_sujet(
    pole_slug: str,
    sujet_slug: str,
    sujet_update: ForumSujetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Modifier un sujet (auteur, staff ou expert du pôle)"""
    sujet_result = await db.execute(
        select(ForumSujet).where(ForumSujet.slug == sujet_slug)
    )
    sujet = sujet_result.scalars().first()
    if not sujet:
        raise HTTPException(status_code=404, detail="Sujet non trouvé.")
    if sujet.author_id != current_user.id and not _peut_animer(current_user, sujet.pole_id):
        raise HTTPException(status_code=403, detail="Action non autorisée.")
    for key, value in sujet_update.model_dump(exclude_unset=True).items():
        setattr(sujet, key, value)
    await db.commit()
    await db.refresh(sujet)
    return sujet


@forum_router.delete("/poles/{pole_slug}/sujets/{sujet_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sujet(
    pole_slug: str,
    sujet_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Supprimer un sujet (auteur, staff ou expert du pôle)"""
    sujet_result = await db.execute(
        select(ForumSujet).where(ForumSujet.slug == sujet_slug)
    )
    sujet = sujet_result.scalar_one_or_none()
    if not sujet:
        raise HTTPException(status_code=404, detail="Sujet non trouvé.")
    if sujet.author_id != current_user.id and not _peut_animer(current_user, sujet.pole_id):
        raise HTTPException(status_code=403, detail="Action non autorisée.")
    # Fichiers du sujet et de ses messages (les lignes partent en cascade)
    ids_commentaires = (await db.execute(
        select(ForumCommentaire.id).where(ForumCommentaire.sujet_id == sujet.id)
    )).scalars().all()
    pieces = (await db.execute(
        select(ForumPieceJointe).where(
            or_(ForumPieceJointe.sujet_id == sujet.id, ForumPieceJointe.commentaire_id.in_(ids_commentaires or [0]))
        )
    )).scalars().all()
    await db.delete(sujet)
    await db.commit()
    forum_medias.supprimer_fichiers(pieces)
    return None


# ─────────────────────────────────────────────────────
# COMMENTAIRES
# ─────────────────────────────────────────────────────

@forum_router.post(
    "/poles/{pole_slug}/sujets/{sujet_slug}/commentaires",
    response_model=ForumCommentaireRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_commentaire(
    pole_slug: str,
    sujet_slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Ajouter un message à un sujet (utilisateur connecté). JSON {content} ou
    multipart (content, fichiers) pour joindre photos, audio, vidéos.
    Refusé si la discussion est close.
    """
    sujet_result = await db.execute(
        select(ForumSujet).where(ForumSujet.slug == sujet_slug)
    )
    sujet = sujet_result.scalars().first()
    if not sujet:
        raise HTTPException(status_code=404, detail="Sujet non trouvé.")
    if sujet.est_clos:
        raise HTTPException(status_code=409, detail="Cette discussion est close : elle n'accepte plus de messages.")

    champs, fichiers = await _lire_message(request)
    content = (champs.get("content") or "").strip()
    if not content and not fichiers:
        raise HTTPException(status_code=422, detail="Écrivez un message ou joignez un fichier.")

    pieces = await forum_medias.enregistrer_fichiers(fichiers)
    db_comment = ForumCommentaire(
        content=content,
        sujet_id=sujet.id,
        author_id=current_user.id,
        author_name=_nom_auteur(current_user),
    )
    try:
        db.add(db_comment)
        await db.flush()
        for piece in pieces:
            piece.commentaire_id = db_comment.id
            db.add(piece)
        # Update comments_count
        sujet.comments_count += 1
        await db.commit()
    except Exception:
        await db.rollback()
        forum_medias.supprimer_fichiers(pieces)
        raise
    await db.refresh(db_comment)
    groupes = await _pieces_par(db, commentaire_ids=[db_comment.id])
    return ForumCommentaireRead(
        id=db_comment.id,
        content=db_comment.content,
        sujet_id=db_comment.sujet_id,
        author_id=db_comment.author_id,
        author_name=db_comment.author_name,
        created_at=db_comment.created_at,
        updated_at=db_comment.updated_at,
        pieces_jointes=groupes.get(db_comment.id, []),
    )


@forum_router.delete("/commentaires/{commentaire_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_commentaire(
    commentaire_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Supprimer un commentaire (auteur, staff ou expert du pôle)"""
    result = await db.execute(
        select(ForumCommentaire).where(ForumCommentaire.id == commentaire_id)
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Commentaire non trouvé.")
    sujet_result = await db.execute(
        select(ForumSujet).where(ForumSujet.id == comment.sujet_id)
    )
    sujet = sujet_result.scalars().first()
    if comment.author_id != current_user.id and not _peut_animer(current_user, sujet.pole_id if sujet else None):
        raise HTTPException(status_code=403, detail="Action non autorisée.")

    # Decrement count
    if sujet and sujet.comments_count > 0:
        sujet.comments_count -= 1

    pieces = (await db.execute(
        select(ForumPieceJointe).where(ForumPieceJointe.commentaire_id == comment.id)
    )).scalars().all()
    await db.delete(comment)
    await db.commit()
    forum_medias.supprimer_fichiers(pieces)
    return None


# ─────────────────────────────────────────────────────
# SYNTHÈSE DES DISCUSSIONS
# ─────────────────────────────────────────────────────

async def _sujet_pour_staff(db: AsyncSession, sujet_id: int, current_user: User) -> tuple:
    sujet = (await db.execute(select(ForumSujet).where(ForumSujet.id == sujet_id))).scalars().first()
    if not sujet:
        raise HTTPException(status_code=404, detail="Sujet non trouvé.")
    if not _peut_animer(current_user, sujet.pole_id):
        raise HTTPException(status_code=403, detail="Action non autorisée.")
    pole = (await db.execute(select(PoleConcertation).where(PoleConcertation.id == sujet.pole_id))).scalars().first()
    return sujet, pole


@forum_router.get("/sujets/{sujet_id}/contributions", response_model=ContributionsSujetRead)
async def contributions_sujet(
    sujet_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Toutes les idées d'une discussion rassemblées pour la synthèse (staff ou expert du pôle) :
    chaque contribution avec son auteur, son OSC, sa date et ses médias,
    les statistiques de participation et un brouillon de synthèse automatique.
    """
    sujet, pole = await _sujet_pour_staff(db, sujet_id, current_user)
    commentaires = (await db.execute(
        select(ForumCommentaire).where(ForumCommentaire.sujet_id == sujet.id).order_by(ForumCommentaire.created_at)
    )).scalars().all()
    groupes = await _pieces_par(db, sujet_id=sujet.id, commentaire_ids=[c.id for c in commentaires])

    # OSC de chaque auteur
    auteurs = {c.author_id for c in commentaires if c.author_id} | ({sujet.author_id} if sujet.author_id else set())
    osc_par_auteur: dict = {}
    if auteurs:
        rows = (await db.execute(
            select(User.id, Osc.name).join(Osc, Osc.id == User.osc_id).where(User.id.in_(auteurs))
        )).all()
        osc_par_auteur = {uid: nom for uid, nom in rows}

    contributions = [
        ContributionRead(
            id=c.id,
            auteur=c.author_name or "Anonyme",
            osc=osc_par_auteur.get(c.author_id),
            date=c.created_at,
            contenu=c.content or "",
            pieces_jointes=groupes.get(c.id, []),
        )
        for c in commentaires
    ]
    pour_brouillon = [
        {"auteur": c.auteur, "osc": c.osc, "date": c.date, "contenu": c.contenu, "medias": len(c.pieces_jointes)}
        for c in contributions
    ]
    pole_nom = pole.name if pole else ""
    return ContributionsSujetRead(
        sujet=ForumSujetRead.model_validate(sujet),
        pole_nom=pole_nom,
        pole_slug=pole.slug if pole else "",
        contributions=contributions,
        nb_contributions=len(contributions),
        nb_participants=len({c.auteur for c in contributions}),
        nb_osc=len({c.osc for c in contributions if c.osc}),
        mots_cles=mots_cles([sujet.content] + [c.contenu for c in contributions]),
        brouillon=brouillon_synthese(sujet.title, sujet.content, pole_nom, pour_brouillon),
    )


@forum_router.patch("/sujets/{sujet_id}/synthese", response_model=ForumSujetRead)
async def enregistrer_synthese(
    sujet_id: int,
    payload: SyntheseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Enregistre la synthèse d'une discussion et/ou la clôt (staff ou expert du pôle). Une
    synthèse vide la retire ; rouvrir la discussion (est_clos=false) permet
    de nouveau les messages.
    """
    sujet, _ = await _sujet_pour_staff(db, sujet_id, current_user)
    donnees = payload.model_dump(exclude_unset=True)
    if "synthese" in donnees:
        texte = (donnees["synthese"] or "").strip()
        sujet.synthese = texte or None
        sujet.synthese_par = _nom_auteur(current_user) if texte else None
        sujet.synthese_le = datetime.now(timezone.utc) if texte else None
    if "est_clos" in donnees and donnees["est_clos"] is not None:
        sujet.est_clos = bool(donnees["est_clos"])
    await db.commit()
    await db.refresh(sujet)
    return sujet
