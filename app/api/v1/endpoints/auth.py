# app/api/v1/endpoints/auth.py
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from datetime import timedelta
from app.models.users import User
from app.database.session import get_db
from app.schemas.users import UserRead, UserCreate
from app.schemas.auth import Token
from app.core.security import get_password_hash, verify_password, create_access_token, create_refresh_token
from app.core.config import settings
from app.services.user_service import UserService

auth_router = APIRouter()

@auth_router.post("/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(
            (User.email == form_data.username) | (User.username == form_data.username)
        )
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Convert user.id (which is a UUID object) to a string using str()
    user_id_str = str(user.id)
    access_token = create_access_token(data={"sub": user_id_str})
    return {"access_token": access_token, "token_type": "bearer"}


@auth_router.post("/register", response_model=UserRead)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalar_one_or_none():
        raise HTTPException(400, "Email already registered")

    hashed_password = get_password_hash(user_in.password)
    user = User(
        email=user_in.email,
        username=user_in.username or user_in.email.split("@")[0],
        password=hashed_password,
        first_name=user_in.first_name,
        last_name=user_in.last_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@auth_router.post("/refresh")
async def refresh_token(refresh_token: str, db: AsyncSession = Depends(get_db)):
    # Simple validation (you can expand with blacklist)
    from jose import jwt, JWTError
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        user_id = int(payload["sub"])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    new_access = create_access_token(data={"sub": str(user.id)})
    return {"access_token": new_access, "token_type": "bearer"}


@auth_router.post("/logout")
async def logout():
    return {"message": "Logout endpoint"}