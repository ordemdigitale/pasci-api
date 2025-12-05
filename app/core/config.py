# app/core/config.py | Configuration management
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from typing import Optional

load_dotenv()

class Settings(BaseSettings):
  # Project
  PROJECT_NAME: str = "PASCI API"
  DESCRIPTION: str = "API REST pour la plateforme des CRASC"
  
  # Database
  DATABASE_URL: Optional[str] = None

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