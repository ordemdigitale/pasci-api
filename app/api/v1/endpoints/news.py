from uuid import UUID
from datetime import date

from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, File, Form
from sqlmodel import select, desc
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List

from app.database.session import get_db
from app.models.news import News, NewsBase
from app.schemas.news import NewsCreate, NewsRead

news_router = APIRouter()

@news_router.post("/") #, response_model=NewsRead, status_code=status.HTTP_201_CREATED
async def create_news(
  file: UploadFile = File(...),
  title: str = Form(""),
  published_date: date = Form(...),
  db: AsyncSession = Depends(get_db)
):
  """ Create a news article with an image upload """
  news_data = NewsCreate(
    title="Title added manually",
    image="Image added manually",
    published_date=date(2025, 11, 27)
  )
  # Convert the request schema (Pydantic) into a mapped SQLModel instance
  db_news = News(**news_data.model_dump())
  db.add(db_news)
  await db.commit()
  await db.refresh(db_news)
  return db_news

@news_router.get("/", response_model=List[NewsRead], status_code=status.HTTP_200_OK)
async def get_news(db: AsyncSession = Depends(get_db)):
  """Get all news articles"""
  result = await db.execute(select(News).order_by(desc(News.created_at)))
  news_articles = result.scalars().all()
  return news_articles


@news_router.get("/{news_id}", response_model=NewsRead, status_code=status.HTTP_200_OK)
async def get_news_by_id(news_id: UUID, db: AsyncSession = Depends(get_db)):
  """Get a single news article by UUID"""
  news_item = await db.get(News, news_id)
  if not news_item:
    raise HTTPException(status_code=404, detail="News not found")
  return news_item
