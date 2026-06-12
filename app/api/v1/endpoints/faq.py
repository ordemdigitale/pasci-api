from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.auth import get_current_staff_user
from app.database.session import get_db
from app.models.faq import Faq
from app.models.users import User

faq_router = APIRouter()


class FaqRead(BaseModel):
    id: int
    question: str
    answer: str
    ordre: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FaqCreate(BaseModel):
    question: str
    answer: str
    ordre: int = 0
    is_active: bool = True


class FaqUpdate(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None
    ordre: Optional[int] = None
    is_active: Optional[bool] = None


@faq_router.get("/", response_model=List[FaqRead])
async def list_faq(db: AsyncSession = Depends(get_db)):
    """Liste les questions actives de la FAQ."""
    result = await db.execute(
        select(Faq)
        .where(Faq.is_active == True)
        .order_by(Faq.ordre.asc(), Faq.id.asc())
    )
    return result.scalars().all()


@faq_router.get("/all", response_model=List[FaqRead])
async def list_all_faq(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Liste toutes les questions de la FAQ, y compris les inactives."""
    result = await db.execute(select(Faq).order_by(Faq.ordre.asc(), Faq.id.asc()))
    return result.scalars().all()


@faq_router.post("/", response_model=FaqRead, status_code=status.HTTP_201_CREATED)
async def create_faq(
    payload: FaqCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    faq = Faq(**payload.model_dump())
    db.add(faq)
    await db.commit()
    await db.refresh(faq)
    return faq


@faq_router.patch("/{faq_id}", response_model=FaqRead)
async def update_faq(
    faq_id: int,
    payload: FaqUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    result = await db.execute(select(Faq).where(Faq.id == faq_id))
    faq = result.scalar_one_or_none()
    if not faq:
        raise HTTPException(status_code=404, detail="Question FAQ introuvable.")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(faq, key, value)

    await db.commit()
    await db.refresh(faq)
    return faq


@faq_router.delete("/{faq_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_faq(
    faq_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    result = await db.execute(select(Faq).where(Faq.id == faq_id))
    faq = result.scalar_one_or_none()
    if not faq:
        raise HTTPException(status_code=404, detail="Question FAQ introuvable.")

    await db.delete(faq)
    await db.commit()
    return None
