from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, computed_field
from uuid import UUID
import json

# Schemas for Jobs
class JobsBase(BaseModel):
    title: str
    employer: str
    description: str
    location: str
    type: str
    is_expired: bool = False
    publication_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    missions: Optional[str] = None
    requirements: Optional[str] = None
    benefits: Optional[str] = None


class JobsCreate(JobsBase):
    pass


class JobsRead(JobsBase):
    id: UUID
    slug: str
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def missions_list(self) -> List[Dict[str, str]]:
        """Parse missions JSON to list"""
        if self.missions:
            try:
                return json.loads(self.missions)
            except:
                return []
        return []

    @computed_field
    @property
    def requirements_list(self) -> List[str]:
        """Parse requirements JSON to list"""
        if self.requirements:
            try:
                return json.loads(self.requirements)
            except:
                return []
        return []

    @computed_field
    @property
    def benefits_list(self) -> List[Dict[str, str]]:
        """Parse benefits JSON to list"""
        if self.benefits:
            try:
                return json.loads(self.benefits)
            except:
                return []
        return []


class JobsUpdate(BaseModel):
    title: Optional[str] = None
    employer: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    type: Optional[str] = None
    is_expired: Optional[bool] = False
    publication_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    missions: Optional[str] = None
    requirements: Optional[str] = None
    benefits: Optional[str] = None