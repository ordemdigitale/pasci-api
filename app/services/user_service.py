from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models.users import User
from app.schemas.users import UserCreate, UserUpdate
from app.core.security import get_password_hash
from uuid import UUID

class UserService:
  @staticmethod
  async def get_user_by_email(db: AsyncSession, email: str) -> User:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()
  
  @staticmethod
  async def get_user_by_username(db: AsyncSession, username: str) -> User:
      result = await db.execute(select(User).where(User.username == username))
      return result.scalar_one_or_none()
  
  @staticmethod
  async def get_user_by_id(db: AsyncSession, user_id: UUID) -> User:
     result = await db.execute(select(User).where(User.id == user_id))
     return result.scalar_one_or_none()
  

  @staticmethod
  async def update_user(
     db: AsyncSession,
     user_id: UUID,
     user_update: UserUpdate
  ) -> User:
     user = await UserService.get_user_by_id(db, user_id)
     if not user:
        raise HTTPException(
           status_code=status.HTTP_404_NOT_FOUND,
           detail="User not found"
        )
     
     update_data = user_update.model_dump(exclude_unset=True)
     for field, value in update_data.items():
        setattr(user, field, value)
     
     await db.commit()
     await db.refresh(user)
     return user
  

  @staticmethod
  async def authenticate_user(
     db: AsyncSession,
     username: str,
     password: str
  ) -> User:
     # Try to find by email or username
     user = await UserService.get_user_by_email(db, username)
     if not user:
        user = await UserService.get_user_by_username(db, username)

     if not user or not user.check_password(password):
        return None
     
     return user