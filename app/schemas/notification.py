from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class NotificationRead(BaseModel):
    id: int
    user_id: UUID
    title: str
    message: str
    type: str
    link_url: Optional[str] = None
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NotificationUnreadCount(BaseModel):
    unread_count: int
