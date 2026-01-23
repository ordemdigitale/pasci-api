# app/api/v1/endpoints/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from sqlmodel import select, desc

from app.core.auth import get_current_user, get_current_superuser, get_current_staff_user
from app.database.session import get_db
from app.models.users import User
from app.schemas.users import UserCreate, UserUpdate, UserRead, UserUpdateAdmin, ChangePassword
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


@users_router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
   user: UserCreate,
   db: AsyncSession = Depends(get_db),
   current_user: User = Depends(get_current_staff_user)
) -> User:
    """Create a new user (staff only)"""
    return await UserService.create_user(db, user)


@users_router.put("/{user_id}", response_model=UserRead)
async def update_user_by_admin(
   user_id: UUID,
   user_update: UserUpdateAdmin,
   db: AsyncSession = Depends(get_db),
   current_user: User = Depends(get_current_staff_user)
):
    """Update any user (staff only, can update permissions)"""
    return await UserService.update_user_admin(db, user_id, user_update)


@users_router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
   user_id: UUID,
   db: AsyncSession = Depends(get_db),
   current_user: User = Depends(get_current_superuser)
):
    """Delete a user (superuser only)"""
    await UserService.delete_user(db, user_id)
    return None


@users_router.post("/me/change-password")
async def change_my_password(
   password_data: ChangePassword,
   current_user: User = Depends(get_current_user),
   db: AsyncSession = Depends(get_db)
):
   """Change current user's password"""
   await UserService.change_password(db, current_user, password_data)
   return {"message": "Password changed successfully"}


@users_router.get("/verify-token")
def verify_token_endpoint(current_user: User = Depends(get_current_user)):
   """Verify if token is valid"""
   return {
      "valid": True,
      "user": {
         "id": current_user.id,
         "email": current_user.email,
         "username": current_user.username,
         "is_staff": current_user.is_staff,
         "is_superuser": current_user.is_superuser
      }
   }