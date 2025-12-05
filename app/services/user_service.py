from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models.users import User
from app.schemas.users import UserCreate, UserUpdate
from app.core.security import get_password_hash