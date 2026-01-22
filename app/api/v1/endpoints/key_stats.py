from fastapi import APIRouter, HTTPException, status, Depends, Form
from sqlalchemy.orm import selectinload, joinedload
from sqlmodel import asc, desc, select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional, List

from app.database.session import get_db
from app.schemas.key_stats import(
  KeyStatsCreate,
  KeyStatsRead,
  KeyStatsUpdate
)
from app.models.key_stats import KeyStats

key_stats_router = APIRouter()

# create: POST
@key_stats_router.post("", response_model=KeyStatsCreate, status_code=status.HTTP_201_CREATED)
async def create_key_stat(stats: KeyStatsCreate, db: AsyncSession = Depends(get_db)) -> KeyStats:
  result = await db.execute(select(KeyStats).where(KeyStats.name == stats.name))
  if result.scalars().first(): raise HTTPException(status_code=409, detail="Chiffre clé existe déjà.")
  db_stats = KeyStats(**stats.model_dump())
  db.add(db_stats)
  await db.commit()
  await db.refresh(db_stats)
  return db_stats

# read: GET
## read all
@key_stats_router.get("", response_model=List[KeyStatsRead], status_code=status.HTTP_200_OK)
async def get_key_stats(db: AsyncSession = Depends(get_db)):
  result = await db.execute(select(KeyStats).order_by(asc(KeyStats.id)))
  key_stats = result.scalars().all()
  return key_stats

### read single
@key_stats_router.get("/{key_stats_id}", response_model=KeyStatsRead, status_code=status.HTTP_200_OK)
async def get_key_stat(key_stats_id: int, db: AsyncSession = Depends(get_db)):
  result = await db.execute(select(KeyStats).where(KeyStats.id == key_stats_id))
  key_stats = result.scalars().first()
  if not key_stats:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chiffre clé non trouvé.")

  return key_stats


## update: PATCH
@key_stats_router.patch("/{key_stats_id}", response_model=KeyStatsRead, status_code=status.HTTP_200_OK)
async def update_key_stat(key_stats_id: int, key_stats_update: KeyStatsUpdate, db: AsyncSession = Depends(get_db)):
  # fetch existing resource by slug
  result = await db.execute(select(KeyStats).where(KeyStats.id == key_stats_id))
  key_stats = result.scalars().first()
  if not key_stats:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chiffre clé non trouvé.")
  # extract fields provided in the request (exclude unset ones)
  update_data = key_stats_update.model_dump(exclude_unset=True)
  # update the database object attributes
  for key, value in update_data.items():
    setattr(key_stats, key, value)

  # persist changes
  await db.commit()
  await db.refresh(key_stats)
  return key_stats


## delete: DELETE
@key_stats_router.delete("/{key_stats_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_key_stat(key_stats_id: int, db: AsyncSession = Depends(get_db)):
  """ Supprimer un chiffre clé """
  result = await db.execute(select(KeyStats).where(KeyStats.id == key_stats_id))
  key_stats = result.scalar_one_or_none()
  # raise 404 if not exist
  if not key_stats:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail=f"Chiffre clé {key_stats_id} non trouvé."
    )
  await db.delete(key_stats)
  await db.commit()
  return None