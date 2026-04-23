# api/v1/endpoints/adhesion.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import select, asc, desc
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Optional

from app.database.session import get_db
from app.models.adhesion import DemandeAdhesion
from app.schemas.adhesion import DemandeAdhesionCreate, DemandeAdhesionRead, DemandeAdhesionUpdate

adhesion_router = APIRouter()


@adhesion_router.post("", response_model=DemandeAdhesionRead, status_code=status.HTTP_201_CREATED)
async def create_demande(data: DemandeAdhesionCreate, db: AsyncSession = Depends(get_db)):
    """Soumettre une nouvelle demande d'adhésion"""
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
):
    """Lister toutes les demandes d'adhésion"""
    query = select(DemandeAdhesion).order_by(desc(DemandeAdhesion.created_at)).offset(skip).limit(limit)
    if statut:
        query = select(DemandeAdhesion).where(DemandeAdhesion.statut == statut).order_by(desc(DemandeAdhesion.created_at)).offset(skip).limit(limit)
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


@adhesion_router.patch("/{demande_id}", response_model=DemandeAdhesionRead, status_code=status.HTTP_200_OK)
async def update_demande(demande_id: int, data: DemandeAdhesionUpdate, db: AsyncSession = Depends(get_db)):
    """Mettre à jour le statut d'une demande (approuver / rejeter)"""
    result = await db.execute(select(DemandeAdhesion).where(DemandeAdhesion.id == demande_id))
    demande = result.scalar_one_or_none()
    if not demande:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demande non trouvée.")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(demande, key, value)
    await db.commit()
    await db.refresh(demande)
    return demande


@adhesion_router.delete("/{demande_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_demande(demande_id: int, db: AsyncSession = Depends(get_db)):
    """Supprimer une demande d'adhésion"""
    result = await db.execute(select(DemandeAdhesion).where(DemandeAdhesion.id == demande_id))
    demande = result.scalar_one_or_none()
    if not demande:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demande non trouvée.")
    await db.delete(demande)
    await db.commit()
