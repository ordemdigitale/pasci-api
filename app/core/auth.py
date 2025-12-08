from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from uuid import UUID
from jose import JWTError, jwt
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.models.users import User
from app.database.session import get_db
from app.core.security import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

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
    payload = jwt.encode(token, _get_secret_key(), algorithm=settings.ALGORITHM)
    user_id: UUID = payload.get("sub")
    if user_id is None:
      raise credentials_exception
  except JWTError:
    raise credentials_exception
  
  result = await db.execute(select(User).where(User.id == user_id))
  user = result.scalar_one_or_none()
  if user is None or not user.is_active:
    raise credentials_exception
  return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# Optional: Superuser only
async def get_current_superuser(user: User = Depends(get_current_active_user)):
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough privileges")
    return user