# app/api/v1/endpoints/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from sqlmodel import select, desc

from app.database.session import get_db
from app.models.users import User
from app.schemas.users import UserCreate, UserUpdate, UserRead

users_router = APIRouter()

@users_router.get("/", response_model=List[UserRead], status_code=status.HTTP_200_OK)
async def get_users(db: AsyncSession = Depends(get_db)):
    """ Gett all users """
    result = await db.execute(select(User).order_by(desc(User.date_joined)))
    all_users = result.scalars().all()
    return all_users


@users_router.get("/{user_id}")
async def get_user(user_id: int):
    return {"message": f"Get user with ID {user_id}"}


@users_router.get("/{user_id}", response_model=UserRead, status_code=status.HTTP_200_OK)
async def get_news_by_id(user_id: UUID, db: AsyncSession = Depends(get_db)):
  """ Get a single user by UUID (ID) """
  user = await db.get(User, user_id)
  if not user:
    raise HTTPException(status_code=404, detail="User not found")
  return user


@users_router.post("/", response_model=UserCreate)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)) -> User:
    """ Create a new user """
    db_user = User(**user.model_dump())
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


@users_router.put("/{user_id}")
async def update_user(user_id: int):
    return {"message": f"Update user {user_id}"}


@users_router.delete("/{user_id}")
async def delete_user(user_id: int):
    return {"message": f"Delete user {user_id}"}