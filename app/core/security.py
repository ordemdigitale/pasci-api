# app/core/security.py | Security utilities
from fastapi import HTTPException, status
from datetime import datetime, timedelta, UTC
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def _get_secret_key() -> str:
  """Return SECRET_KEY as str or raise if not configured (helps static type checkers)."""
  if settings.SECRET_KEY is None:
    raise RuntimeError("SECRET_KEY is not configured")
  return settings.SECRET_KEY

def verify_password(plain_password: str, hashed_password: str) -> bool:
  """Verify password (similar to Django's check_password)"""
  return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
  """Hash password (similar to Django's make_password)"""
  return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
  to_encode = data.copy()
  expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
  to_encode.update({"exp": expire, "type": "access"})
  encode_jwt = jwt.encode(to_encode, _get_secret_key(), algorithm=settings.ALGORITHM)
  return encode_jwt

def create_refresh_token(data: dict):
  to_encode = data.copy()
  expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
  to_encode.update({"exp": expire, "type": "refresh"})
  return jwt.encode(to_encode, _get_secret_key(), algorithm=settings.ALGORITHM)

def verify_token(token: str, token_type: str) -> dict:
  """Verify JWT token and return the payload if valid."""
  try:
    payload = jwt.decode(token, _get_secret_key(), algorithms=[settings.ALGORITHM])
    if payload.get("type") != token_type:
      raise JWTError("Invalid token type")
    return payload
  except JWTError as e:
    raise JWTError(f"Token verification failed: {str(e)}")