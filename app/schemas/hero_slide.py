# schemas/hero_slide.py
from pydantic import BaseModel, computed_field
from typing import Optional
from datetime import datetime, timezone
from app.core.config import settings


def _url(chemin: Optional[str]) -> Optional[str]:
    if not chemin:
        return None
    if chemin.startswith("/") or chemin.startswith("http"):
        return chemin
    return f"{settings.API_BASE_URL}/static/{chemin}"


class HeroSlideRead(BaseModel):
    id: int
    image_path: str
    title: Optional[str] = None
    description: Optional[str] = None
    type: str
    ordre: int
    is_active: bool
    date_expiration: Optional[datetime] = None
    objectif: Optional[str] = None
    resume: Optional[str] = None
    article: Optional[str] = None
    photo1_path: Optional[str] = None
    photo2_path: Optional[str] = None
    created_at: datetime

    @computed_field
    @property
    def image_url(self) -> str:
        return _url(self.image_path) or ""

    @computed_field
    @property
    def photo1_url(self) -> Optional[str]:
        return _url(self.photo1_path)

    @computed_field
    @property
    def photo2_url(self) -> Optional[str]:
        return _url(self.photo2_path)

    @computed_field
    @property
    def est_expiree(self) -> bool:
        if not self.date_expiration:
            return False
        fin = self.date_expiration if self.date_expiration.tzinfo else self.date_expiration.replace(tzinfo=timezone.utc)
        return fin <= datetime.now(timezone.utc)

    @computed_field
    @property
    def a_descriptif(self) -> bool:
        """« Voir plus » mène à la page de la slide quand elle a un descriptif."""
        return bool(self.objectif or self.resume or self.article or self.photo1_path or self.photo2_path)

    class Config:
        from_attributes = True


class HeroSlideUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    ordre: Optional[int] = None
    is_active: Optional[bool] = None
