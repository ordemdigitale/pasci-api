# app/core/database/session.py | Database session management
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from app.core.config import settings
import logging

from sqlmodel import SQLModel

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Base class for models
Base = declarative_base()

try:
    # Create async engine using the ASYNC_DATABASE_URL from settings
    async_engine = create_async_engine(
        settings.ASYNC_DATABASE_URL,
        echo=settings.DEBUG,
        future=True,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=20,
        max_overflow=40,
		)
    logger.info("✅ Database engine created successfully")
    logger.info(f"Database URL: {settings.DATABASE_URL}")
except Exception as e:
    logger.error(f"❌ Failed to create database engine: {e}")
    raise

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Dependency to get database session
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()