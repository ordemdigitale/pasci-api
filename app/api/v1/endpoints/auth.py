# app/api/v1/endpoints/auth.py
from fastapi import APIRouter
from app.schemas.users import UserRead, UserCreate
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.users import User
from app.database.session import get_db
from sqlmodel import select

auth_router = APIRouter()

@auth_router.post("/login")
async def login():
    return {"message": "Login endpoint"}


@auth_router.post("/register", response_model=UserRead)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalar_one_or_none():
        raise HTTPException(400, "Email already registered")

    user = User(**user_in.dict(exclude={"password"}))
    user.set_password(user_in.password)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@auth_router.post("/refresh")
async def refresh_token():
    return {"message": "Refresh token endpoint"}

@auth_router.post("/logout")
async def logout():
    return {"message": "Logout endpoint"}