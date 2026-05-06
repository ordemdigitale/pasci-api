from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from uuid import UUID
from typing import Optional
from jose import JWTError, jwt
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.models.users import User
from app.database.session import get_db
from app.core.security import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def _get_secret_key() -> str:
  """Return SECRET_KEY as str or raise if not configured (helps static type checkers)."""
  if settings.SECRET_KEY is None:
    raise RuntimeError("SECRET_KEY is not configured")
  return settings.SECRET_KEY

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
  credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
  )
  try:
    payload = jwt.decode(
       token,
       _get_secret_key(), # or _get_secret_key() function
       algorithms=[settings.ALGORITHM]
    )
    user_id: UUID = payload.get("sub")
    if user_id is None:
      raise credentials_exception
  except JWTError as e:
    raise credentials_exception from e
  
  try:
     user_uuid = UUID(user_id)
  except ValueError:
     raise credentials_exception
  
  result = await db.execute(select(User).where(User.id == user_uuid))
  user = result.scalar_one_or_none()
  if user is None or not user.is_active:
    raise credentials_exception
  return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_staff_user(current_user: User = Depends(get_current_user)) -> User:
   """ Gett current staff user """
   if not current_user.is_staff:
      raise HTTPException(
         status_code=status.HTTP_403_FORBIDDEN,
         detail="The user does not have enough privileges"
      )
   return current_user


async def get_current_redacteur_or_staff(current_user: User = Depends(get_current_user)) -> User:
    """Autorise les rédacteurs ET le staff (pour créer du contenu)."""
    if not (current_user.is_staff or current_user.is_redacteur):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux rédacteurs et au staff."
        )
    return current_user


# Optional: Superuser only
async def get_current_superuser(user: User = Depends(get_current_active_user)):
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough privileges")
    return user


# Auth optionnelle : retourne l'utilisateur connecté ou None
_optional_oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

async def get_optional_current_user(
    token: Optional[str] = Depends(_optional_oauth2),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Retourne l'utilisateur connecté, ou None si non authentifié."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, _get_secret_key(), algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if not user_id:
            return None
        user_uuid = UUID(user_id)
    except (JWTError, ValueError):
        return None
    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()
    return user if user and user.is_active else None


async def get_current_staff_or_superuser(current_user: User = Depends(get_current_user)) -> User:
    """Autorise le staff (admin CRASC) ET les superusers."""
    if not (current_user.is_staff or current_user.is_superuser):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs CRASC et aux superadmins."
        )
    return current_user


def check_crasc_ownership(user: User, crasc_id: Optional[int]) -> None:
    """Lève une 403 si un staff tente d'accéder aux données d'un autre CRASC."""
    if user.is_superuser:
        return
    if crasc_id is None or user.crasc_id != crasc_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'avez pas accès aux données de ce CRASC."
        )