# app/api/v1/endpoints/numeros_utiles.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.database.session import get_db
from app.models.numero_utile import NumeroUtile
from app.core.auth import get_current_staff_user
from app.models.users import User

numeros_utiles_router = APIRouter()


class NumeroUtileRead(BaseModel):
    id: int
    categorie: str
    label: str
    numero: str
    description: Optional[str] = None
    ordre: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NumeroUtileCreate(BaseModel):
    categorie: str
    label: str
    numero: str
    description: Optional[str] = None
    ordre: int = 0
    is_active: bool = True


class NumeroUtileUpdate(BaseModel):
    categorie: Optional[str] = None
    label: Optional[str] = None
    numero: Optional[str] = None
    description: Optional[str] = None
    ordre: Optional[int] = None
    is_active: Optional[bool] = None


# ── Public ────────────────────────────────────────────

@numeros_utiles_router.get("/", response_model=List[NumeroUtileRead])
async def list_numeros(db: AsyncSession = Depends(get_db)):
    """Liste tous les numéros actifs, groupés par catégorie (public)."""
    result = await db.execute(
        select(NumeroUtile)
        .where(NumeroUtile.is_active == True)
        .order_by(NumeroUtile.categorie, NumeroUtile.ordre)
    )
    return result.scalars().all()


@numeros_utiles_router.get("/all", response_model=List[NumeroUtileRead])
async def list_all_numeros(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Liste tous les numéros (staff only — inclut inactifs)."""
    result = await db.execute(
        select(NumeroUtile).order_by(NumeroUtile.categorie, NumeroUtile.ordre)
    )
    return result.scalars().all()


# ── Staff ────────────────────────────────────────────

@numeros_utiles_router.post("/", response_model=NumeroUtileRead, status_code=status.HTTP_201_CREATED)
async def create_numero(
    payload: NumeroUtileCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    numero = NumeroUtile(**payload.model_dump())
    db.add(numero)
    await db.commit()
    await db.refresh(numero)
    return numero


@numeros_utiles_router.patch("/{numero_id}", response_model=NumeroUtileRead)
async def update_numero(
    numero_id: int,
    payload: NumeroUtileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    result = await db.execute(select(NumeroUtile).where(NumeroUtile.id == numero_id))
    numero = result.scalar_one_or_none()
    if not numero:
        raise HTTPException(status_code=404, detail="Numéro introuvable.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(numero, key, value)
    await db.commit()
    await db.refresh(numero)
    return numero


@numeros_utiles_router.delete("/{numero_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_numero(
    numero_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    result = await db.execute(select(NumeroUtile).where(NumeroUtile.id == numero_id))
    numero = result.scalar_one_or_none()
    if not numero:
        raise HTTPException(status_code=404, detail="Numéro introuvable.")
    await db.delete(numero)
    await db.commit()
    return None
