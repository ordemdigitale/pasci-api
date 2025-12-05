# models/items.py
from sqlmodel import SQLModel, Field
from typing import Optional

class Item(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    price: float