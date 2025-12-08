# app/schemas/user.py | SQLModel schemas for User
# schemas/user.py
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from uuid import UUID

class UserCreate(BaseModel):
  email: str
  username: Optional[str] = None
  password: str
  first_name: Optional[str] = None
  last_name: Optional[str] = None

  def password_validator(self) -> None:
    if len(self.password) < 8:
      raise ValueError("Password must be at least 8 characters long")


class UserUpdate(BaseModel):
  email: Optional[str] = None
  username: Optional[str] = None
  first_name: Optional[str] = None
  last_name: Optional[str] = None
  avatar: Optional[str] = None
  bio: Optional[str] = None


class UserRead(BaseModel):
  id: UUID
  email: str
  username: Optional[str]
  first_name: Optional[str]
  last_name: Optional[str]
  is_active: bool
  is_staff: bool
  is_superuser: bool
  date_joined: datetime
  last_login: Optional[datetime]
  avatar: Optional[str]
  bio: Optional[str]

  class Config:
        from_attributes = True  # Replaces orm_mode = True


class UserLogin(BaseModel):
   email: str
   password: str


class Token(BaseModel):
    access_token: str
    token_type: str