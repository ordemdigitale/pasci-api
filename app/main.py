from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.v1.endpoints.items import item_router
from app.api.v1.endpoints.news import news_router
from app.database.session import create_db_and_tables

@asynccontextmanager
async def life_span(app: FastAPI):
    await create_db_and_tables()
    print("Database tables created")
    yield

app = FastAPI(
  title="PASCI API",
  description="API for PASCI application",
  version="1.0.0",
  lifespan=life_span
)

# CORS middleware
app.add_middleware(
  CORSMiddleware,
  allow_origins=["http://localhost:3000"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

app.include_router(item_router, prefix="/api/v1/items", tags=["items"])
app.include_router(news_router, prefix="/api/v1/news", tags=["news"])