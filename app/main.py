import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from starlette.formparsers import MultiPartParser

# Augmenter la limite d'upload à 50 Mo (défaut Starlette = 1 Mo)
MultiPartParser.max_part_size = 50 * 1024 * 1024
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import text
import logging
from app.core.config import settings
from app.database.session import async_engine, Base
from app.core.lifespan import app_lifespan
from app.api.v1.endpoints.auth import auth_router
from app.api.v1.endpoints.users import users_router
from app.api.v1.endpoints.jobs import jobs_router
from app.api.v1.endpoints.crasc import crasc_router
from app.api.v1.endpoints.key_stats import key_stats_router
from app.api.v1.endpoints.ptf import ptf_router
from app.api.v1.endpoints.news import news_router
from app.api.v1.endpoints.stats import stats_router
from app.api.v1.endpoints.search import search_router
from app.api.v1.endpoints.tags import tags_router
from app.api.v1.endpoints.formations import formations_router
from app.api.v1.endpoints.documentation import documentation_router
from app.api.v1.endpoints.offre_projet import offre_projet_router
from app.api.v1.endpoints.forum import forum_router
from app.api.v1.endpoints.annonces import annonces_router
from app.api.v1.endpoints.hero_slides import hero_slides_router
from app.api.v1.endpoints.site_config import site_config_router
from app.api.v1.endpoints.adhesion import adhesion_router
from app.api.v1.endpoints.dons import dons_router
from app.api.v1.endpoints.volontaires import volontaires_router
from app.api.v1.endpoints.visites import visites_router
from app.api.v1.endpoints.numeros_utiles import numeros_utiles_router
from app.admin.config import create_admin_panel

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

# PDFs et fichiers formations (doit être monté AVANT /static générique)
os.makedirs("static/formations/pdf", exist_ok=True)
app.mount("/static/formations", StaticFiles(directory="static/formations"), name="static-formations")

# Images/thumbnails (uploads/images)
app.mount("/static", StaticFiles(directory=settings.UPLOAD_DIR), name="static")

# Session middleware for admin authentication
app.add_middleware(
  SessionMiddleware,
  secret_key=settings.SECRET_KEY or "your-secret-key-change-in-production"
)

# CORS middleware
app.add_middleware(
  CORSMiddleware,
  allow_origins=[
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://plateforme-osci.org",
    "https://www.plateforme-osci.org",
  ],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

# Create admin panel
admin = create_admin_panel(app)

# Include routers
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users_router, prefix="/api/v1/users", tags=["users"])
app.include_router(crasc_router, prefix="/api/v1/crasc", tags=["crasc"])
app.include_router(jobs_router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(key_stats_router, prefix="/api/v1/key-stats", tags=["key-stats"])
app.include_router(ptf_router, prefix="/api/v1/ptf", tags=["ptf"])
app.include_router(offre_projet_router, prefix="/api/v1/offre-projets", tags=["offre-projets"])
app.include_router(news_router, prefix="/api/v1/news", tags=["news"])
app.include_router(tags_router, prefix="/api/v1/tags", tags=["tags"])
app.include_router(formations_router, prefix="/api/v1/formations", tags=["formations"])
app.include_router(documentation_router, prefix="/api/v1/documentation", tags=["documentation"])
app.include_router(stats_router, prefix="/api/v1/stats", tags=["statistics"])
app.include_router(search_router, prefix="/api/v1/search", tags=["search"])
app.include_router(forum_router, prefix="/api/v1/forum", tags=["forum"])
app.include_router(annonces_router, prefix="/api/v1/annonces", tags=["annonces"])
app.include_router(hero_slides_router, prefix="/api/v1/hero-slides", tags=["hero-slides"])
app.include_router(site_config_router, prefix="/api/v1/config", tags=["config"])
app.include_router(adhesion_router, prefix="/api/v1/adhesion", tags=["adhesion"])
app.include_router(dons_router, prefix="/api/v1/dons", tags=["dons"])
app.include_router(volontaires_router, prefix="/api/v1/volontaires", tags=["volontaires"])
app.include_router(visites_router, prefix="/api/v1/visites", tags=["visites"])
app.include_router(numeros_utiles_router, prefix="/api/v1/numeros-utiles", tags=["numeros-utiles"])

@app.get("/")
async def root():
  return {
    "message": "API pour le projet PASCI",
    "status": "running"
  }
