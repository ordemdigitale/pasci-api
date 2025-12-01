# app/core/config.py | Configuration management
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
  # Project
  PROJECT_NAME: str = "PASCI API"
  DESCRIPTION: str = "API REST pour la plateforme des CRASC"
  
  # Database
  DATABASE_URL: Optional[str] = None

  # ImageKit
  IMAGEKIT_PRIVATE_KEY: Optional[str] = None
  IMAGEKIT_PUBLIC_KEY: Optional[str] = None
  IMAGEKIT_URL: Optional[str] = None

  class Config:
    case_sensitive = True
    env_file = ".env"
  
settings = Settings()