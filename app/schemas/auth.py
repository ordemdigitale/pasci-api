# schemas/auth.py
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: UUID

class LoginForm(BaseModel):
    email: str  # Can be username or email
    password: str