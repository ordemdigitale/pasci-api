import os, shutil, uuid
from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Form
from sqlmodel import asc, select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Optional

from app.database.session import get_db
from app.schemas.hero_slide import HeroSlideRead, HeroSlideUpdate
from app.models.hero_slide import HeroSlide
from app.core.config import settings

hero_slides_router = APIRouter()


def _save_image(upload: UploadFile) -> str:
    ext = upload.filename.rsplit(".", 1)[-1].lower() if upload.filename and "." in upload.filename else "jpg"
    filename = f"{uuid.uuid4()}.{ext}"
    path = os.path.join(settings.UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        shutil.copyfileobj(upload.file, f)
    return filename


def _delete_image(image_path: Optional[str]):
    if image_path and not image_path.startswith("/"):
        full = os.path.join(settings.UPLOAD_DIR, image_path)
        if os.path.exists(full):
            os.remove(full)


@hero_slides_router.get("", response_model=List[HeroSlideRead])
async def get_hero_slides(
    active_only: bool = False,
    type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(HeroSlide).order_by(asc(HeroSlide.ordre), asc(HeroSlide.id))
    if active_only:
        query = query.where(HeroSlide.is_active == True)
    if type:
        query = query.where(HeroSlide.type == type)
    result = await db.execute(query)
    return result.scalars().all()


@hero_slides_router.post("", response_model=HeroSlideRead, status_code=status.HTTP_201_CREATED)
async def create_hero_slide(
    image: UploadFile = File(...),
    type: str = Form(default="haut"),
    ordre: int = Form(default=0),
    is_active: bool = Form(default=True),
    db: AsyncSession = Depends(get_db),
):
    filename = _save_image(image)
    slide = HeroSlide(image_path=filename, type=type, ordre=ordre, is_active=is_active)
    db.add(slide)
    await db.commit()
    await db.refresh(slide)
    return slide


@hero_slides_router.patch("/{slide_id}", response_model=HeroSlideRead)
async def update_hero_slide(
    slide_id: int,
    image: Optional[UploadFile] = File(default=None),
    type: Optional[str] = Form(default=None),
    ordre: Optional[int] = Form(default=None),
    is_active: Optional[bool] = Form(default=None),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(HeroSlide).where(HeroSlide.id == slide_id))
    slide = result.scalars().first()
    if not slide:
        raise HTTPException(status_code=404, detail="Slide non trouvé.")

    if image and image.filename:
        _delete_image(slide.image_path)
        slide.image_path = _save_image(image)
    if type is not None:
        slide.type = type
    if ordre is not None:
        slide.ordre = ordre
    if is_active is not None:
        slide.is_active = is_active

    await db.commit()
    await db.refresh(slide)
    return slide


@hero_slides_router.delete("/{slide_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hero_slide(slide_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(HeroSlide).where(HeroSlide.id == slide_id))
    slide = result.scalar_one_or_none()
    if not slide:
        raise HTTPException(status_code=404, detail="Slide non trouvé.")
    _delete_image(slide.image_path)
    await db.delete(slide)
    await db.commit()
    return None
