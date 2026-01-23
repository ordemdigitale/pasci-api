from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models.users import User
from app.schemas.users import UserCreate, UserUpdate, UserUpdateAdmin, ChangePassword
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


  @staticmethod
  async def update_user_admin(
     db: AsyncSession,
     user_id: UUID,
     user_update: UserUpdateAdmin
  ) -> User:
     """Update user by admin (can update permissions)"""
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
  async def change_password(
     db: AsyncSession,
     user: User,
     password_data: ChangePassword
  ) -> bool:
     """Change user password"""
     # Verify old password
     if not user.check_password(password_data.old_password):
        raise HTTPException(
           status_code=status.HTTP_400_BAD_REQUEST,
           detail="Incorrect old password"
        )

     # Set new password
     user.set_password(password_data.new_password)
     await db.commit()
     return True


  @staticmethod
  async def delete_user(db: AsyncSession, user_id: UUID) -> bool:
     """Delete a user"""
     user = await UserService.get_user_by_id(db, user_id)
     if not user:
        raise HTTPException(
           status_code=status.HTTP_404_NOT_FOUND,
           detail="User not found"
        )

     await db.delete(user)
     await db.commit()
     return True


  @staticmethod
  async def create_user(
     db: AsyncSession,
     user_data: UserCreate
  ) -> User:
     """Create a new user"""
     # Check if email already exists
     existing_user = await UserService.get_user_by_email(db, user_data.email)
     if existing_user:
        raise HTTPException(
           status_code=status.HTTP_400_BAD_REQUEST,
           detail="Email already registered"
        )

     # Check if username already exists
     if user_data.username:
        existing_username = await UserService.get_user_by_username(db, user_data.username)
        if existing_username:
           raise HTTPException(
              status_code=status.HTTP_400_BAD_REQUEST,
              detail="Username already taken"
           )

     # Create user
     db_user = User(**user_data.model_dump(exclude={"password"}))
     db_user.set_password(user_data.password)
     db.add(db_user)
     await db.commit()
     await db.refresh(db_user)
     return db_user