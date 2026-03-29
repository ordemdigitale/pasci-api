# app/api/v1/endpoints/forum.py | Forum endpoints
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import slugify as slugify_lib
import time

from app.database.session import get_db
from app.models.forum import PoleConcertation, ForumSujet, ForumCommentaire
from app.models.users import User
from app.schemas.forum import (
    PoleConcertationCreate, PoleConcertationRead, PoleConcertationUpdate,
    ForumSujetCreate, ForumSujetRead, ForumSujetUpdate, ForumSujetDetail,
    ForumCommentaireCreate, ForumCommentaireRead,
)
from app.core.auth import get_current_user, get_current_staff_user

forum_router = APIRouter()


# ─────────────────────────────────────────────────────
# PÔLES
# ─────────────────────────────────────────────────────

@forum_router.get("/poles", response_model=List[PoleConcertationRead])
async def list_poles(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Liste tous les pôles de concertation (public)"""
    result = await db.execute(
        select(PoleConcertation)
        .where(PoleConcertation.is_active == True)
        .order_by(PoleConcertation.name)
        .offset(skip)
        .limit(limit)
    )
    poles = result.scalars().all()

    # Compute sujets_count for each pole
    output = []
    for pole in poles:
        count_result = await db.execute(
            select(func.count(ForumSujet.id)).where(ForumSujet.pole_id == pole.id)
        )
        sujets_count = count_result.scalar() or 0
        pole_data = PoleConcertationRead.model_validate(pole)
        pole_data.sujets_count = sujets_count
        output.append(pole_data)

    return output


@forum_router.post("/poles", response_model=PoleConcertationRead, status_code=status.HTTP_201_CREATED)
async def create_pole(
    pole: PoleConcertationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Créer un pôle (staff only)"""
    db_pole = PoleConcertation(**pole.model_dump())
    db.add(db_pole)
    await db.commit()
    await db.refresh(db_pole)
    pole_data = PoleConcertationRead.model_validate(db_pole)
    pole_data.sujets_count = 0
    return pole_data


@forum_router.get("/poles/{pole_slug}", response_model=PoleConcertationRead)
async def get_pole(pole_slug: str, db: AsyncSession = Depends(get_db)):
    """Détail d'un pôle (public)"""
    result = await db.execute(
        select(PoleConcertation).where(PoleConcertation.slug == pole_slug)
    )
    pole = result.scalars().first()
    if not pole:
        raise HTTPException(status_code=404, detail="Pôle non trouvé.")
    count_result = await db.execute(
        select(func.count(ForumSujet.id)).where(ForumSujet.pole_id == pole.id)
    )
    pole_data = PoleConcertationRead.model_validate(pole)
    pole_data.sujets_count = count_result.scalar() or 0
    return pole_data


@forum_router.patch("/poles/{pole_slug}", response_model=PoleConcertationRead)
async def update_pole(
    pole_slug: str,
    pole_update: PoleConcertationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    result = await db.execute(
        select(PoleConcertation).where(PoleConcertation.slug == pole_slug)
    )
    pole = result.scalars().first()
    if not pole:
        raise HTTPException(status_code=404, detail="Pôle non trouvé.")
    for key, value in pole_update.model_dump(exclude_unset=True).items():
        setattr(pole, key, value)
    if "name" in pole_update.model_dump(exclude_unset=True):
        pole.slug = slugify_lib.slugify(pole.name)
    await db.commit()
    await db.refresh(pole)
    pole_data = PoleConcertationRead.model_validate(pole)
    pole_data.sujets_count = 0
    return pole_data


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
    await db.delete(pole)
    await db.commit()
    return None


# ─────────────────────────────────────────────────────
# SUJETS
# ─────────────────────────────────────────────────────

@forum_router.get("/poles/{pole_slug}/sujets", response_model=List[ForumSujetRead])
async def list_sujets(
    pole_slug: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Liste les sujets d'un pôle (public)"""
    pole_result = await db.execute(
        select(PoleConcertation).where(PoleConcertation.slug == pole_slug)
    )
    pole = pole_result.scalars().first()
    if not pole:
        raise HTTPException(status_code=404, detail="Pôle non trouvé.")

    result = await db.execute(
        select(ForumSujet)
        .where(ForumSujet.pole_id == pole.id)
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
