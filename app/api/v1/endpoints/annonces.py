from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlmodel import asc, select, or_
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List
from datetime import datetime, timezone

from app.database.session import get_db
from app.schemas.annonce import AnnonceCreate, AnnonceRead, AnnonceUpdate
from app.models.annonce import Annonce

annonces_router = APIRouter()


@annonces_router.get("", response_model=List[AnnonceRead], status_code=status.HTTP_200_OK)
async def get_annonces(
    active_only: bool = Query(False, description="Ne retourner que les annonces actives"),
    db: AsyncSession = Depends(get_db),
):
    query = select(Annonce).order_by(asc(Annonce.ordre), asc(Annonce.id))
    if active_only:
        now = datetime.now(timezone.utc)
        query = query.where(Annonce.is_active == True).where(
            or_(Annonce.date_fin == None, Annonce.date_fin > now)
        )
    result = await db.execute(query)
    return result.scalars().all()


@annonces_router.get("/{annonce_id}", response_model=AnnonceRead, status_code=status.HTTP_200_OK)
async def get_annonce(annonce_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Annonce).where(Annonce.id == annonce_id))
    annonce = result.scalars().first()
    if not annonce:
        raise HTTPException(status_code=404, detail="Annonce non trouvée.")
    return annonce


@annonces_router.post("", response_model=AnnonceRead, status_code=status.HTTP_201_CREATED)
async def create_annonce(annonce: AnnonceCreate, db: AsyncSession = Depends(get_db)):
    db_annonce = Annonce(**annonce.model_dump())
    db.add(db_annonce)
    await db.commit()
    await db.refresh(db_annonce)
    return db_annonce


@annonces_router.patch("/{annonce_id}", response_model=AnnonceRead, status_code=status.HTTP_200_OK)
async def update_annonce(annonce_id: int, annonce_update: AnnonceUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Annonce).where(Annonce.id == annonce_id))
    annonce = result.scalars().first()
    if not annonce:
        raise HTTPException(status_code=404, detail="Annonce non trouvée.")
    for key, value in annonce_update.model_dump(exclude_unset=True).items():
        setattr(annonce, key, value)
    await db.commit()
    await db.refresh(annonce)
    return annonce


@annonces_router.delete("/{annonce_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_annonce(annonce_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Annonce).where(Annonce.id == annonce_id))
    annonce = result.scalar_one_or_none()
    if not annonce:
        raise HTTPException(status_code=404, detail="Annonce non trouvée.")
    await db.delete(annonce)
    await db.commit()
    return None
