from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from sqlalchemy import text
import logging
from sqlmodel import SQLModel
from app.database.session import async_engine, Base, get_db
from app.database.test_connection import test_database_connection
from app.core.init_db import create_default_superuser

# Import all models so SQLModel.metadata is populated before create_all
import app.models.users
import app.models.crasc
import app.models.jobs
import app.models.key_stats
import app.models.ptf
import app.models.hero
import app.models.tags
import app.models.formation
import app.models.documentation
import app.models.offre_projet
import app.models.forum

logger = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager
    Handles startup and shutdown events
    Accepts FastAPI app as parameter
    """
    # Startup
    await startup()
    
    yield  # Application runs here
    
    # Shutdown
    await shutdown()


async def startup():
    """Handle application startup"""
    logger.info("🚀 Starting up FastAPI application...")
    
    # Test database connection
    logger.info("🔌 Testing database connection...")
    connected = await test_database_connection()
    if not connected:
        logger.error("❌ Database connection failed!")
        raise RuntimeError("Failed to connect to database")
    
    # Create database tables
    try:
        logger.info("🗄️ Creating database tables...")
        async with async_engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        logger.info("✅ Database tables created successfully!")
    except Exception as e:
        logger.error(f"❌ Failed to create tables: {e}")
        raise

    # Create default superuser
    try:
        logger.info("👤 Initializing default superuser...")
        async for db in get_db():
            await create_default_superuser(db)
            break
    except Exception as e:
        logger.error(f"❌ Failed to initialize default superuser: {e}")
        # Don't raise - app can still run without default user

    logger.info("✅ Startup complete!")


async def shutdown():
    """Handle application shutdown"""
    logger.info("🛑 Shutting down FastAPI application...")
    
    # Dispose of database connections
    logger.info("🔌 Disposing database engine...")
    await async_engine.dispose()
    
    logger.info("✅ Shutdown complete!")