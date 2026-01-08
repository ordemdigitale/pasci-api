from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import logging
from app.core.config import settings
from app.database.session import async_engine, Base
from app.database.test_connection import test_database_connection
from app.core.lifespan import app_lifespan
from app.api.v1.endpoints.auth import auth_router
from app.api.v1.endpoints.users import users_router
from app.api.v1.endpoints.news import news_router
from app.api.v1.endpoints.jobs import jobs_router
from app.api.v1.endpoints.crasc import crasc_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app with lifespan
app = FastAPI(
  title=settings.PROJECT_NAME,
  description=settings.DESCRIPTION,
  version="1.0.0",
  debug=settings.DEBUG,
  lifespan=app_lifespan,
)

# CORS middleware
app.add_middleware(
  CORSMiddleware,
  allow_origins=["http://localhost:3000"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users_router, prefix="/api/v1/users", tags=["users"])
app.include_router(crasc_router, prefix="/api/v1/crasc", tags=["crasc"])
app.include_router(news_router, prefix="/api/v1/news", tags=["news"])
app.include_router(jobs_router, prefix="/api/v1/jobs", tags=["jobs"])

@app.get("/")
async def root():
  return {
    "message": "FastAPI with Modern Lifespan Events",
    "status": "running"
  }