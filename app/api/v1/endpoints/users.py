# app/api/v1/endpoints/users.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
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
   skip: int = Query(0, ge=0, description="Nombre d'enregistrements à ignorer"),
   limit: int = Query(100, ge=1, le=500, description="Nombre d'enregistrements à retourner"),
   current_user: User = Depends(get_current_staff_user),
   db: AsyncSession = Depends(get_db)
):
    """Get all users with pagination. Admin CRASC only sees OSC users from their CRASC."""
    from app.models.crasc import Osc
    query = select(User).order_by(desc(User.date_joined))

    # Admin CRASC: filter to OSC users belonging to their CRASC
    if not current_user.is_superuser and current_user.crasc_id:
        osc_result = await db.execute(
            select(Osc.id).where(Osc.crasc_id == current_user.crasc_id)
        )
        osc_ids = [row[0] for row in osc_result.all()]
        query = query.where(User.osc_id.in_(osc_ids))

    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


@users_router.get("/{user_id}", response_model=UserRead, status_code=status.HTTP_200_OK)
async def get_user_by_id(
   user_id: UUID,
   current_user: User = Depends(get_current_staff_user),
   db: AsyncSession = Depends(get_db)
):
  """ Get a single user by ID (UUID) """
  user = await UserService.get_user_by_id(db, user_id)
  if not user:
     raise HTTPException(status_code=404, detail="User not found")
  # Admin CRASC: restrict to OSC users from their CRASC
  if not current_user.is_superuser and current_user.crasc_id:
      from app.models.crasc import Osc
      if not user.osc_id:
          raise HTTPException(status_code=403, detail="Accès refusé.")
      osc_result = await db.execute(select(Osc).where(Osc.id == user.osc_id))
      osc = osc_result.scalar_one_or_none()
      if not osc or osc.crasc_id != current_user.crasc_id:
          raise HTTPException(status_code=403, detail="Accès refusé.")
  return user


@users_router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
   user: UserCreate,
   db: AsyncSession = Depends(get_db),
   current_user: User = Depends(get_current_staff_user)
) -> User:
    """Create a new user. Admin CRASC can only create rédacteurs for their own CRASC."""
    new_user = await UserService.create_user(db, user)
    # Admin CRASC: force role to rédacteur CRASC only, attached to their CRASC
    if not current_user.is_superuser:
        new_user.is_redacteur = True
        new_user.is_staff = False
        new_user.is_superuser = False
        new_user.crasc_id = current_user.crasc_id
        await db.commit()
        await db.refresh(new_user)
    return new_user


@users_router.put("/{user_id}", response_model=UserRead)
async def update_user_by_admin(
   user_id: UUID,
   user_update: UserUpdateAdmin,
   db: AsyncSession = Depends(get_db),
   current_user: User = Depends(get_current_staff_user)
):
    """Update any user. Admin CRASC cannot escalate privileges (is_staff/is_superuser)."""
    if not current_user.is_superuser:
        # Strip privilege-escalation fields
        user_update.is_superuser = None
        user_update.is_staff = None
        # Ensure crasc_id cannot be changed to another CRASC
        if user_update.crasc_id is not None and user_update.crasc_id != current_user.crasc_id:
            raise HTTPException(status_code=403, detail="Vous ne pouvez pas assigner un autre CRASC.")
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