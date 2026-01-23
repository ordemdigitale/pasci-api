# app/core/init_db.py | Database initialization and default user creation
import logging
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.users import User
from app.core.security import get_password_hash

logger = logging.getLogger(__name__)


async def create_default_superuser(db: AsyncSession) -> None:
    """
    Create a default superuser if no superuser exists.
    Default credentials:
    - Email: admin@pasci.dz
    - Username: admin
    - Password: admin123
    """
    try:
        # Check if any superuser already exists
        result = await db.execute(select(User).where(User.is_superuser == True))
        existing_superuser = result.scalar_one_or_none()

        if existing_superuser:
            logger.info(f"✅ Superuser already exists: {existing_superuser.email}")
            return

        # Create default superuser
        default_password = "admin123"
        hashed_password = get_password_hash(default_password)

        superuser = User(
            email="admin@pasci.dz",
            username="admin",
            password=hashed_password,
            first_name="Admin",
            last_name="PASCI",
            is_active=True,
            is_staff=True,
            is_superuser=True,
        )

        db.add(superuser)
        await db.commit()
        await db.refresh(superuser)

        logger.info("=" * 60)
        logger.info("✅ Default superuser created successfully!")
        logger.info("=" * 60)
        logger.info("📧 Email: admin@pasci.dz")
        logger.info("👤 Username: admin")
        logger.info("🔑 Password: admin123")
        logger.info("=" * 60)
        logger.warning("⚠️  Please change the default password after first login!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Failed to create default superuser: {e}")
        await db.rollback()
        raise
