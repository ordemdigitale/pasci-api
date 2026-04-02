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
  POSTGRES_USER: str = "pasci_user"
  POSTGRES_PASSWORD: str = "Pasci#12345"
  POSTGRES_HOST: str = "localhost"
  POSTGRES_PORT: str = "5432"
  POSTGRES_DB: str = "pasci_db"
  
  # Uploads directory
  UPLOAD_DIR: str = "uploads/images"

  # API Base URL (for constructing static file URLs)
  API_BASE_URL: str = "https://api.plateforme-osci.org"

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

  # CinetPay — renseigner ces valeurs dans .env une fois l'API acquise
  CINETPAY_API_KEY: Optional[str] = None        # ex: "123456789"
  CINETPAY_SITE_ID: Optional[str] = None        # ex: "987654321"
  CINETPAY_API_URL: str = "https://api-checkout.cinetpay.com/v2/payment"
  CINETPAY_CURRENCY: str = "XOF"                # XOF pour FCFA (UEMOA) / XAF pour FCFA (CEMAC)
  CINETPAY_RETURN_URL: str = "http://localhost:3000/formations/paiement/retour"
  CINETPAY_NOTIFY_URL: str = "http://localhost:8000/api/v1/formations/paiement/webhook"

  @property
  def cinetpay_configured(self) -> bool:
    """Retourne True si CinetPay est configuré (clés renseignées)"""
    return bool(self.CINETPAY_API_KEY and self.CINETPAY_SITE_ID)

  class Config:
    case_sensitive = True
    env_file = ".env"
  
settings = Settings()
