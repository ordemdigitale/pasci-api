# schemas/hero_slide.py
from pydantic import BaseModel, computed_field
from typing import Optional
from datetime import datetime
from app.core.config import settings


class HeroSlideRead(BaseModel):
    id: int
    image_path: str
    type: str
    ordre: int
    is_active: bool
    created_at: datetime

    @computed_field
    @property
    def image_url(self) -> str:
        if self.image_path.startswith("/"):
            return self.image_path
        return f"{settings.API_BASE_URL}/static/{self.image_path}"

    class Config:
        from_attributes = True


class HeroSlideUpdate(BaseModel):
    ordre: Optional[int] = None
    is_active: Optional[bool] = None
