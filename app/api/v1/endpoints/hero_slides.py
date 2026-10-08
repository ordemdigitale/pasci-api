import os, shutil, uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Form
from sqlalchemy import or_
from sqlmodel import asc, select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Optional

from app.database.session import get_db
from app.schemas.hero_slide import HeroSlideRead
from app.models.hero_slide import HeroSlide
from app.models.users import User
from app.core.auth import get_current_staff_user, get_optional_current_user
from app.core.config import settings

hero_slides_router = APIRouter()

ALLOWED_IMAGE_EXT = {"jpg", "jpeg", "png", "webp"}
ALLOWED_IMAGE_MIME = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024


def _save_image(upload: UploadFile) -> str:
    ext = upload.filename.rsplit(".", 1)[-1].lower() if upload.filename and "." in upload.filename else "jpg"
    if ext not in ALLOWED_IMAGE_EXT:
        raise HTTPException(status_code=400, detail="Format invalide. Utilisez JPG, PNG ou WebP.")
    if upload.content_type and upload.content_type not in ALLOWED_IMAGE_MIME:
        raise HTTPException(status_code=400, detail="Type de fichier invalide. Utilisez JPG, PNG ou WebP.")
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    upload.file.seek(0, os.SEEK_END)
    file_size = upload.file.tell()
    upload.file.seek(0)
    if file_size > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="L'image ne doit pas dépasser 5MB.")
    filename = f"{uuid.uuid4()}.{ext}"
    path = os.path.join(settings.UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        shutil.copyfileobj(upload.file, f)
    return filename


def _delete_image(image_path: Optional[str]):
    if image_path and not image_path.startswith("/"):
        full = os.path.join(settings.UPLOAD_DIR, os.path.basename(image_path))
        if os.path.exists(full):
            os.remove(full)


def _parse_date(valeur: Optional[str]) -> Optional[datetime]:
    """Date d'expiration : « AAAA-MM-JJ » (fin de journée) ou « AAAA-MM-JJTHH:MM ». Vide = aucune."""
    if valeur is None or not valeur.strip():
        return None
    texte = valeur.strip()
    try:
        if len(texte) == 10:
            d = datetime.fromisoformat(texte).replace(hour=23, minute=59, second=59)
        else:
            d = datetime.fromisoformat(texte.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=422, detail="Date d'expiration invalide (AAAA-MM-JJ).")
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _non_expiree():
    """Désactivation automatique : une slide dont la date d'expiration est passée n'est plus affichée."""
    return or_(HeroSlide.date_expiration.is_(None), HeroSlide.date_expiration > datetime.now(timezone.utc))


@hero_slides_router.get("", response_model=List[HeroSlideRead])
async def get_hero_slides(
    active_only: bool = False,
    type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(HeroSlide).order_by(asc(HeroSlide.ordre), asc(HeroSlide.id))
    if active_only:
        query = query.where(HeroSlide.is_active == True, _non_expiree())  # noqa: E712
    if type:
        query = query.where(HeroSlide.type == type)
    result = await db.execute(query)
    return result.scalars().all()


@hero_slides_router.get("/{slide_id}", response_model=HeroSlideRead)
async def get_hero_slide(
    slide_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Descriptif d'une slide (page « Voir plus ») : slide active et non expirée, sauf pour l'administration."""
    slide = await db.get(HeroSlide, slide_id)
    est_staff = bool(current_user and (current_user.is_staff or current_user.is_superuser))
    if not slide or (not est_staff and (not slide.is_active or HeroSlideRead.model_validate(slide).est_expiree)):
        raise HTTPException(status_code=404, detail="Slide non trouvé.")
    return slide


@hero_slides_router.post("", response_model=HeroSlideRead, status_code=status.HTTP_201_CREATED)
async def create_hero_slide(
    image: UploadFile = File(...),
    title: Optional[str] = Form(default=None),
    description: Optional[str] = Form(default=None),
    type: str = Form(default="haut"),
    ordre: int = Form(default=0),
    is_active: bool = Form(default=True),
    date_expiration: Optional[str] = Form(default=None),
    objectif: Optional[str] = Form(default=None),
    resume: Optional[str] = Form(default=None),
    article: Optional[str] = Form(default=None),
    photo1: Optional[UploadFile] = File(default=None),
    photo2: Optional[UploadFile] = File(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    if type not in ("haut", "bas"):
        raise HTTPException(status_code=422, detail="Section inconnue (haut ou bas).")
    slide = HeroSlide(
        image_path=_save_image(image),
        title=title,
        description=description,
        type=type,
        ordre=ordre,
        is_active=is_active,
        date_expiration=_parse_date(date_expiration),
        objectif=(objectif or "").strip() or None,
        resume=(resume or "").strip() or None,
        article=(article or "").strip() or None,
        photo1_path=_save_image(photo1) if photo1 and photo1.filename else None,
        photo2_path=_save_image(photo2) if photo2 and photo2.filename else None,
    )
    db.add(slide)
    await db.commit()
    await db.refresh(slide)
    return slide


@hero_slides_router.patch("/{slide_id}", response_model=HeroSlideRead)
async def update_hero_slide(
    slide_id: int,
    image: Optional[UploadFile] = File(default=None),
    title: Optional[str] = Form(default=None),
    description: Optional[str] = Form(default=None),
    type: Optional[str] = Form(default=None),
    ordre: Optional[int] = Form(default=None),
    is_active: Optional[bool] = Form(default=None),
    date_expiration: Optional[str] = Form(default=None, description="Vide = sans date d'expiration"),
    objectif: Optional[str] = Form(default=None),
    resume: Optional[str] = Form(default=None),
    article: Optional[str] = Form(default=None),
    photo1: Optional[UploadFile] = File(default=None),
    photo2: Optional[UploadFile] = File(default=None),
    supprimer_photo1: bool = Form(default=False),
    supprimer_photo2: bool = Form(default=False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    result = await db.execute(select(HeroSlide).where(HeroSlide.id == slide_id))
    slide = result.scalars().first()
    if not slide:
        raise HTTPException(status_code=404, detail="Slide non trouvé.")

    if image and image.filename:
        _delete_image(slide.image_path)
        slide.image_path = _save_image(image)
    if title is not None:
        slide.title = title
    if description is not None:
        slide.description = description
    if type is not None:
        if type not in ("haut", "bas"):
            raise HTTPException(status_code=422, detail="Section inconnue (haut ou bas).")
        slide.type = type
    if ordre is not None:
        slide.ordre = ordre
    if is_active is not None:
        slide.is_active = is_active
    if date_expiration is not None:
        slide.date_expiration = _parse_date(date_expiration)
    if objectif is not None:
        slide.objectif = objectif.strip() or None
    if resume is not None:
        slide.resume = resume.strip() or None
    if article is not None:
        slide.article = article.strip() or None
    for champ, fichier, supprimer in (("photo1_path", photo1, supprimer_photo1), ("photo2_path", photo2, supprimer_photo2)):
        if (fichier and fichier.filename) or supprimer:
            _delete_image(getattr(slide, champ))
            setattr(slide, champ, _save_image(fichier) if fichier and fichier.filename else None)

    await db.commit()
    await db.refresh(slide)
    return slide


@hero_slides_router.delete("/{slide_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hero_slide(
    slide_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    result = await db.execute(select(HeroSlide).where(HeroSlide.id == slide_id))
    slide = result.scalar_one_or_none()
    if not slide:
        raise HTTPException(status_code=404, detail="Slide non trouvé.")
    for chemin in (slide.image_path, slide.photo1_path, slide.photo2_path):
        _delete_image(chemin)
    await db.delete(slide)
    await db.commit()
    return None
