# app/api/v1/endpoints/forum.py | Forum endpoints
import json
import os, shutil, uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlmodel import select, desc, func
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import List, Optional, Union
import slugify as slugify_lib
import time

from app.core.config import settings
from app.database.session import get_db
from app.models.forum import (
    PoleConcertation,
    PoleSondage,
    PoleSondageOption,
    PoleSondageVote,
    ForumSujet,
    ForumCommentaire,
)
from app.models.crasc import Osc
from app.models.users import User
from app.schemas.forum import (
    PoleConcertationCreate, PoleConcertationRead, PoleConcertationUpdate,
    PoleSondageCreate, PoleSondageRead, PoleSondageUpdate, PoleSondageVoteCreate,
    PoleSondageOptionRead, PoleMembreRead,
    ForumSujetCreate, ForumSujetRead, ForumSujetUpdate, ForumSujetDetail,
    ForumCommentaireCreate, ForumCommentaireRead,
)
from app.core.auth import get_current_user, get_current_staff_user, get_current_superuser, get_optional_current_user

ALLOWED_IMAGE_EXT = ["jpg", "jpeg", "png", "webp"]

async def _save_image(upload: UploadFile) -> str:
    """Save an uploaded image to UPLOAD_DIR and return the filename."""
    ext = (upload.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_IMAGE_EXT:
        raise HTTPException(status_code=400, detail=f"Format invalide. Formats acceptés: {ALLOWED_IMAGE_EXT}")
    contents = await upload.read()
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
)
SONDAGE_LOAD_OPTIONS = (
    selectinload(PoleSondage.options).selectinload(PoleSondageOption.votes),
    selectinload(PoleSondage.votes),
    selectinload(PoleSondage.pole).selectinload(PoleConcertation.oscs),
)


def _json_list(values: List[str]) -> str:
    return json.dumps(values, ensure_ascii=False)


def _regions_from_pole(pole: PoleConcertation) -> List[str]:
    seen = set()
    regions = []
    for osc in pole.oscs or []:
        region_name = (osc.region_nom or "").strip()
        if not region_name and getattr(osc, "region", None):
            region_name = (osc.region.name or "").strip()
        if region_name and region_name.lower() not in seen:
            seen.add(region_name.lower())
            regions.append(region_name)
    return sorted(regions, key=str.lower)


async def _pole_response(db: AsyncSession, pole: PoleConcertation) -> PoleConcertationRead:
    count_result = await db.execute(
        select(func.count(ForumSujet.id)).where(ForumSujet.pole_id == pole.id)
    )
    osc_count = len(pole.oscs or [])
    pole_data = PoleConcertationRead.model_validate(pole)
    pole_data.sujets_count = count_result.scalar() or 0
    pole_data.nb_osc_membres = osc_count
    pole_data.nb_membres_actifs = osc_count
    pole_data.regions_influence = _json_list(_regions_from_pole(pole))
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


def _user_can_access_pole(user: User, pole: PoleConcertation) -> bool:
    if user.is_superuser or user.is_staff:
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
    current_user: User = Depends(get_current_superuser),
):
    """Créer un pôle (superuser only)"""
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
    image: Union[UploadFile, str, None] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    pole = await _get_pole_by_slug(db, pole_slug)
    if not pole:
        raise HTTPException(status_code=404, detail="Pôle non trouvé.")

    if isinstance(image, UploadFile) and image.filename:
        _delete_image(pole.image_path)
        pole.image_path = await _save_image(image)

    if name is not None:
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
    current_user: User = Depends(get_current_superuser),
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
                region_nom=osc.region_nom,
                ville=osc.ville,
                thumbnail_url=thumbnail_url,
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


@forum_router.post("/poles/{pole_slug}/sujets", response_model=ForumSujetRead, status_code=status.HTTP_201_CREATED)
async def create_sujet(
    pole_slug: str,
    sujet: ForumSujetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Créer un sujet dans un pôle (utilisateur connecté)"""
    pole_result = await db.execute(
        select(PoleConcertation).where(PoleConcertation.slug == pole_slug)
    )
    pole = pole_result.scalars().first()
    if not pole:
        raise HTTPException(status_code=404, detail="Pôle non trouvé.")

    author_name = current_user.username or f"{current_user.first_name or ''} {current_user.last_name or ''}".strip() or current_user.email
    base_slug = slugify_lib.slugify(sujet.title)
    unique_slug = f"{base_slug}-{int(time.time())}"

    db_sujet = ForumSujet(
        title=sujet.title,
        slug=unique_slug,
        content=sujet.content,
        pole_id=pole.id,
        author_id=current_user.id,
        author_name=author_name,
    )
    db.add(db_sujet)
    await db.commit()
    await db.refresh(db_sujet)
    return db_sujet


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
        )
        for c in commentaires
    ]

    return ForumSujetDetail(
        id=sujet.id,
        title=sujet.title,
        slug=sujet.slug,
        content=sujet.content,
        pole_id=sujet.pole_id,
        author_id=sujet.author_id,
        author_name=sujet.author_name,
        is_pinned=sujet.is_pinned,
        views_count=sujet.views_count,
        comments_count=sujet.comments_count,
        created_at=sujet.created_at,
        updated_at=sujet.updated_at,
        commentaires=commentaires_data,
    )


@forum_router.patch("/poles/{pole_slug}/sujets/{sujet_slug}", response_model=ForumSujetRead)
async def update_sujet(
    pole_slug: str,
    sujet_slug: str,
    sujet_update: ForumSujetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Modifier un sujet (auteur ou staff)"""
    sujet_result = await db.execute(
        select(ForumSujet).where(ForumSujet.slug == sujet_slug)
    )
    sujet = sujet_result.scalars().first()
    if not sujet:
        raise HTTPException(status_code=404, detail="Sujet non trouvé.")
    if sujet.author_id != current_user.id and not current_user.is_staff:
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
    """Supprimer un sujet (auteur ou staff)"""
    sujet_result = await db.execute(
        select(ForumSujet).where(ForumSujet.slug == sujet_slug)
    )
    sujet = sujet_result.scalar_one_or_none()
    if not sujet:
        raise HTTPException(status_code=404, detail="Sujet non trouvé.")
    if sujet.author_id != current_user.id and not current_user.is_staff:
        raise HTTPException(status_code=403, detail="Action non autorisée.")
    await db.delete(sujet)
    await db.commit()
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
    commentaire: ForumCommentaireCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Ajouter un commentaire à un sujet (utilisateur connecté)"""
    sujet_result = await db.execute(
        select(ForumSujet).where(ForumSujet.slug == sujet_slug)
    )
    sujet = sujet_result.scalars().first()
    if not sujet:
        raise HTTPException(status_code=404, detail="Sujet non trouvé.")

    author_name = current_user.username or f"{current_user.first_name or ''} {current_user.last_name or ''}".strip() or current_user.email
    db_comment = ForumCommentaire(
        content=commentaire.content,
        sujet_id=sujet.id,
        author_id=current_user.id,
        author_name=author_name,
    )
    db.add(db_comment)

    # Update comments_count
    sujet.comments_count += 1
    await db.commit()
    await db.refresh(db_comment)
    return db_comment


@forum_router.delete("/commentaires/{commentaire_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_commentaire(
    commentaire_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Supprimer un commentaire (auteur ou staff)"""
    result = await db.execute(
        select(ForumCommentaire).where(ForumCommentaire.id == commentaire_id)
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Commentaire non trouvé.")
    if comment.author_id != current_user.id and not current_user.is_staff:
        raise HTTPException(status_code=403, detail="Action non autorisée.")

    # Decrement count
    sujet_result = await db.execute(
        select(ForumSujet).where(ForumSujet.id == comment.sujet_id)
    )
    sujet = sujet_result.scalars().first()
    if sujet and sujet.comments_count > 0:
        sujet.comments_count -= 1

    await db.delete(comment)
    await db.commit()
    return None
