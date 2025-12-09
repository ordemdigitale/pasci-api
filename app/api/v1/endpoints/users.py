# app/api/v1/endpoints/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from sqlmodel import select, desc

from app.core.auth import get_current_user, get_current_superuser
from app.database.session import get_db
from app.models.users import User
from app.schemas.users import UserCreate, UserUpdate, UserRead
from app.services.user_service import UserService

users_router = APIRouter()

@users_router.get("/me", response_model=UserRead)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
   """Get current user profile"""
   return current_user


@users_router.put("/me", response_model=UserRead)
async def update_current_user_profile(
   user_update: UserUpdate,
   current_user: User = Depends(get_current_user),
   db: AsyncSession = Depends(get_db)
):
   """ Update current user profile """
   return await UserService.update_user(db, current_user.id, user_update)


@users_router.get("/", response_model=List[UserRead], status_code=status.HTTP_200_OK)
async def get_users(
   current_user: User = Depends(get_current_superuser),
   db: AsyncSession = Depends(get_db)
):
    """ Gett all users """
    result = await db.execute(select(User).order_by(desc(User.date_joined)))
    all_users = result.scalars().all()
    return all_users


@users_router.get("/{user_id}", response_model=UserRead, status_code=status.HTTP_200_OK)
async def get_user_by_id(
   user_id: UUID,
   current_user: User = Depends(get_current_superuser),
   db: AsyncSession = Depends(get_db)
):
  """ Get a single user by ID (UUID) """
  user = await UserService.get_user_by_id(db, user_id)
  if not user:
     raise HTTPException(status_code=404, detail="User not found")
  return user


@users_router.post("/", response_model=UserCreate)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)) -> User:
    """ Create a new user """
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user.email))
    if result.scalar_one_or_none():
       raise HTTPException(400, "User with this e-mail already registered")

    db_user = User(**user.model_dump(exclude={"password"}))
    db_user.set_password(user.password)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


@users_router.get("/verify-token")
def verify_token_endpoint(current_user: User = Depends(get_current_user)):
   return {
      "valid": True,
      "user": {
         "id": current_user.id,
         "email": current_user.email
      }
   }
   


@users_router.put("/{user_id}")
async def update_user(user_id: int):
    return {"message": f"Update user {user_id}"}


@users_router.delete("/{user_id}")
async def delete_user(user_id: int):
    return {"message": f"Delete user {user_id}"}