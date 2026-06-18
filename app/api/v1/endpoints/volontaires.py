from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import select, desc
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Optional

from app.database.session import get_db
from app.models.volontaire import Volontaire
from app.models.users import User
from app.schemas.volontaire import VolontaireCreate, VolontaireRead, VolontaireUpdate
from app.core.auth import get_current_staff_user

volontaires_router = APIRouter()


@volontaires_router.post("", response_model=VolontaireRead, status_code=status.HTTP_201_CREATED)
async def create_volontaire(data: VolontaireCreate, db: AsyncSession = Depends(get_db)):
    """Soumettre une candidature de volontariat."""
    volontaire = Volontaire(**data.model_dump())
    db.add(volontaire)
    await db.commit()
    await db.refresh(volontaire)
    return volontaire


@volontaires_router.get("", response_model=List[VolontaireRead], status_code=status.HTTP_200_OK)
async def get_volontaires(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    statut: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Lister toutes les candidatures (staff only)."""
    query = select(Volontaire).order_by(desc(Volontaire.created_at))
    if statut:
        query = query.where(Volontaire.statut == statut)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@volontaires_router.get("/{volontaire_id}", response_model=VolontaireRead)
async def get_volontaire(
    volontaire_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    result = await db.execute(select(Volontaire).where(Volontaire.id == volontaire_id))
    v = result.scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=404, detail="Candidature non trouvée.")
    return v


@volontaires_router.patch("/{volontaire_id}", response_model=VolontaireRead)
async def update_volontaire(
    volontaire_id: int,
    data: VolontaireUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    result = await db.execute(select(Volontaire).where(Volontaire.id == volontaire_id))
    v = result.scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=404, detail="Candidature non trouvée.")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(v, key, value)
    await db.commit()
    await db.refresh(v)
    return v


@volontaires_router.delete("/{volontaire_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_volontaire(
    volontaire_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    result = await db.execute(select(Volontaire).where(Volontaire.id == volontaire_id))
    v = result.scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=404, detail="Candidature non trouvée.")
    await db.delete(v)
    await db.commit()
