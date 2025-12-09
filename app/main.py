from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.api.v1.endpoints.auth import auth_router
from app.api.v1.endpoints.users import users_router
from app.api.v1.endpoints.items import item_router
from app.api.v1.endpoints.news import news_router
from app.database.session import create_db_and_tables

@asynccontextmanager
async def life_span(app: FastAPI):
    await create_db_and_tables()
    print("Database tables created")
    yield

app = FastAPI(
  title=settings.PROJECT_NAME,
  description=settings.DESCRIPTION,
  version="1.0.0",
#  lifespan=life_span
)

# CORS middleware
app.add_middleware(
  CORSMiddleware,
  allow_origins=["http://localhost:3000"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users_router, prefix="/api/v1/users", tags=["users"])
app.include_router(item_router, prefix="/api/v1/items", tags=["items"])
app.include_router(news_router, prefix="/api/v1/news", tags=["news"])