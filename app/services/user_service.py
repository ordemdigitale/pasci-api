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