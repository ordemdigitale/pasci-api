# app/core/config.py | Configuration management
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from typing import Optional

load_dotenv()

class Settings(BaseSettings):
  # Project
  PROJECT_NAME: str = "PASCI API"
  DESCRIPTION: str = "API REST pour la plateforme des CRASC"
  DEBUG: bool = True
  
  # Database
  #DATABASE_URL: Optional[str] = None
  POSTGRES_USER: str = "admin"
  POSTGRES_PASSWORD: str = "admin"
  POSTGRES_HOST: str = "localhost"
  POSTGRES_PORT: str = "5432"
  POSTGRES_DB: str = "pascidb"
  
  # Uploads directory
  UPLOAD_DIR: str = "uploads/images"

  # Construct DATABASE_URL
  @property
  def DATABASE_URL(self) -> str:
    return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
  
  @property
  def ASYNC_DATABASE_URL(self) -> str:
    return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

  # Security
  SECRET_KEY: Optional[str] = None
  ALGORITHM: str = "HS256"
  ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
  REFRESH_TOKEN_EXPIRE_DAYS: int = 7

  # ImageKit
  IMAGEKIT_PRIVATE_KEY: Optional[str] = None
  IMAGEKIT_PUBLIC_KEY: Optional[str] = None
  IMAGEKIT_URL: Optional[str] = None

  class Config:
    case_sensitive = True
    env_file = ".env"
  
settings = Settings()