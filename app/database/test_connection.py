import asyncio
from sqlalchemy import text
from app.database.session import async_engine
import logging

logger = logging.getLogger(__name__)


async def test_database_connection():
    """Test database connection and print details"""
    try:
        async with async_engine.connect() as conn:
            # Test connection
            result = await conn.execute(text("SELECT version();"))
            version = result.fetchone()
            logger.info(f"✅ Connected to PostgreSQL: {version[0]}")
            
            # Get database name
            result = await conn.execute(text("SELECT current_database();"))
            db_name = result.fetchone()
            logger.info(f"✅ Database: {db_name[0]}")
            
            # Get current user
            result = await conn.execute(text("SELECT current_user;"))
            user = result.fetchone()
            logger.info(f"✅ User: {user[0]}")
            
            # Test connection pool
            result = await conn.execute(text("SELECT 1"))
            test_value = result.fetchone()
            logger.info(f"✅ Connection test query: {test_value[0]}")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


async def get_database_info():
    """Get detailed database information"""
    try:
        async with async_engine.connect() as conn:
            info = {}
            
            # Version
            result = await conn.execute(text("SELECT version();"))
            info['version'] = result.fetchone()[0]
            
            # Database name
            result = await conn.execute(text("SELECT current_database();"))
            info['database'] = result.fetchone()[0]
            
            # User
            result = await conn.execute(text("SELECT current_user;"))
            info['user'] = result.fetchone()[0]
            
            # Connection count
            result = await conn.execute(
                text("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database();")
            )
            info['active_connections'] = result.fetchone()[0]
            
            # Database size
            result = await conn.execute(
                text("SELECT pg_database_size(current_database()) / 1024 / 1024 as size_mb;")
            )
            info['size_mb'] = round(result.fetchone()[0], 2)
            
            return info
            
    except Exception as e:
        logger.error(f"Failed to get database info: {e}")
        return None


if __name__ == "__main__":
    # Test the connection
    asyncio.run(test_database_connection())
    
    # Get detailed info
    info = asyncio.run(get_database_info())
    if info:
        print("\n📊 Database Information:")
        for key, value in info.items():
            print(f"{key}: {value}")