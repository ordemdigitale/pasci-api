from unittest import result
from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List
from app.database.session import get_db
from app.models.items import Item
from app.schemas.items import ItemCreate, ItemRead, ItemUpdate

item_router = APIRouter()

@item_router.get("/", response_model=List[ItemRead], status_code=status.HTTP_200_OK)
async def get_items(db: AsyncSession = Depends(get_db)):
  """ Get all items """
  result = await db.execute(select(Item))
  items = result.scalars().all()
  return items

@item_router.post("/", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
async def create_item(item: ItemCreate, db: AsyncSession = Depends(get_db)) -> Item:
  """ Create a new item """
  # Convert the request schema (Pydantic) into a mapped SQLModel instance
  db_item = Item(**item.model_dump())
  db.add(db_item)
  await db.commit()
  await db.refresh(db_item)
  return db_item