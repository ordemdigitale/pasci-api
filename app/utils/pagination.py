# app/utils/pagination.py | Pagination utilities
from fastapi import Query
from typing import TypeVar, Generic, List
from pydantic import BaseModel

T = TypeVar('T')

class PaginationParams(BaseModel):
    """Standard pagination parameters"""
    skip: int = Query(0, ge=0, description="Nombre d'enregistrements à ignorer")
    limit: int = Query(100, ge=1, le=500, description="Nombre d'enregistrements à retourner (max 500)")

class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response"""
    items: List[T]
    total: int
    skip: int
    limit: int
    has_more: bool

    class Config:
        from_attributes = True

def create_pagination_params(skip: int = 0, limit: int = 100):
    """
    Helper to create pagination parameters
    Usage in endpoint:
        skip: int = Query(0, ge=0, description="...")
        limit: int = Query(100, ge=1, le=500, description="...")
    """
    return {
        "skip": skip,
        "limit": limit
    }
