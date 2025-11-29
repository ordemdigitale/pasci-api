# schemas/items.py
from pydantic import BaseModel
from datetime import datetime

class ItemCreate(BaseModel):
    name: str
    description: str | None = None
    price: float

class ItemRead(BaseModel):
    id: int
    name: str
    description: str | None
    price: float
    #created_at: datetime

class ItemUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = None