# app/schemas/formation.py
"""
Pydantic schemas for Formation model
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl


class FormationBase(BaseModel):
    """Base Formation schema"""
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    trainer: Optional[str] = Field(None, max_length=200)
    location: Optional[str] = Field(None, max_length=200)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    registration_deadline: Optional[datetime] = None
    max_participants: Optional[int] = Field(None, ge=1)
    registration_link: Optional[str] = Field(None, max_length=500)
    materials_link: Optional[str] = Field(None, max_length=500)
    is_published: bool = False


class FormationCreate(FormationBase):
    """Schema for creating a formation"""
    crasc_id: Optional[int] = None
    osc_id: Optional[int] = None


class FormationUpdate(BaseModel):
    """Schema for updating a formation"""
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = None
    trainer: Optional[str] = Field(None, max_length=200)
    location: Optional[str] = Field(None, max_length=200)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    registration_deadline: Optional[datetime] = None
    max_participants: Optional[int] = Field(None, ge=1)
    current_participants: Optional[int] = Field(None, ge=0)
    registration_link: Optional[str] = Field(None, max_length=500)
    materials_link: Optional[str] = Field(None, max_length=500)
    is_published: Optional[bool] = None
    is_full: Optional[bool] = None
    is_completed: Optional[bool] = None
    crasc_id: Optional[int] = None
    osc_id: Optional[int] = None


class FormationRead(FormationBase):
    """Schema for reading a formation"""
    id: int
    slug: str
    current_participants: int
    is_full: bool
    is_completed: bool
    thumbnail_path: str
    crasc_id: Optional[int] = None
    osc_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FormationReadWithRelations(FormationRead):
    """Formation with CRASC and OSC details"""
    crasc: Optional[dict] = None
    osc: Optional[dict] = None
