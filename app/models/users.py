# app/models/user.py | User model definition
from datetime import datetime
from passlib.context import CryptContext
from sqlalchemy import Column, Text, DateTime
from sqlalchemy.sql import func
from sqlmodel import SQLModel, Field
from typing import Optional
from uuid import uuid4, UUID

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(SQLModel, table=True):
  # Core fields
  # Use UUID primary key to avoid integer auto-increment reliance
  id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
  email: str = Field(max_length=255, unique=True, index=True, nullable=False)
  username: Optional[str] = Field(default=None, max_length=150, unique=True, index=True)

  # Password
  password: str = Field(max_length=255, nullable=False)

  # Personal info
  first_name: Optional[str] = Field(default=None, max_length=150)
  last_name: Optional[str] = Field(default=None, max_length=150)

  # Permission flags
  is_active: bool = Field(default=True)
  is_staff: bool = Field(default=False)
  is_superuser: bool = Field(default=False)

  # Timestamps
  date_joined: Optional[datetime] = Field(
      default_factory=datetime.utcnow,
      sa_column=Column(DateTime(timezone=True), server_default=func.now())
  )
  last_login: Optional[datetime] = Field(
      default=None,
      sa_column=Column(DateTime(timezone=True), nullable=True)
  )

  # Extra fields
  avatar: Optional[str] = Field(default=None, max_length=500)
  bio: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))

  # ——— Additional methods ———

  def set_password(self, raw_password: str):
      """Hash and set the password"""
      self.password = pwd_context.hash(raw_password)

  def check_password(self, raw_password: str) -> bool:
      """Verify a raw password against the stored hash"""
      return pwd_context.verify(raw_password, self.password)

  @property
  def full_name(self) -> str:
      """Return 'First Last' or empty string"""
      return f"{self.first_name or ''} {self.last_name or ''}".strip()

  @property
  def is_authenticated(self) -> bool:
      """Always True for logged-in users (FastAPI compatibility)"""
      return True

  def has_perm(self, perm: str) -> bool:
      """Permission check — superusers have all perms"""
      return self.is_superuser

  def has_module_perms(self, app_label: str) -> bool:
      """Module-level permission check"""
      return self.is_superuser

  def get_username(self) -> str:
      """Return username or fallback to email"""
      return self.username or self.email

  def __str__(self) -> str:
      return self.get_username()

  # Optional: Nice representation in admin/logs
  def __repr__(self) -> str:
      return f"<User {self.id}: {self.get_username()} ({'active' if self.is_active else 'inactive'})>"