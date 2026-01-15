import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
import logging
from app.core.config import settings
from app.database.session import async_engine, Base
from app.core.lifespan import app_lifespan
from app.api.v1.endpoints.auth import auth_router
from app.api.v1.endpoints.users import users_router
from app.api.v1.endpoints.jobs import jobs_router
from app.api.v1.endpoints.crasc import crasc_router
from app.api.v1.endpoints.hero import hero_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the directory once when the app starts
if not os.path.exists(settings.UPLOAD_DIR):
  os.makedirs(settings.UPLOAD_DIR)

# Create FastAPI app with lifespan
app = FastAPI(
  title=settings.PROJECT_NAME,
  description=settings.DESCRIPTION,
  version="1.0.0",
  debug=settings.DEBUG,
  lifespan=app_lifespan,
)

app.mount("/static", StaticFiles(directory=settings.UPLOAD_DIR), name="static")

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
app.include_router(jobs_router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(hero_router, prefix="/api/v1/super-hero", tags=["heroes"])

@app.get("/")
async def root():
  return {
    "message": "API pour le projet PASCI",
    "status": "running"
  }