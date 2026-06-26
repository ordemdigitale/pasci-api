from typing import Optional
from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.notification import Notification


async def create_notification(
    db: AsyncSession,
    *,
    user_id: UUID,
    title: str,
    message: str,
    type: str = "info",
    link_url: Optional[str] = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=type,
        link_url=link_url,
    )
    db.add(notification)
    return notification
