from uuid import UUID
from datetime import date

from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, File, Form
from sqlmodel import select, desc
from sqlmodel.ext.asyncio.session import AsyncSession
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
from typing import List

from app.database.session import get_db
from app.models.news import News, NewsBase, NewsArticle
from app.schemas.news import NewsCreate, NewsRead, NewsArticleCreate, NewsArticleRead
from app.utils.preview_text_generator import generate_excerpt

from app.services.imagekit_config import imagekit
import shutil
import os
import tempfile

news_router = APIRouter()

@news_router.post("/") #, response_model=NewsRead, status_code=status.HTTP_201_CREATED
async def create_news(
  file: UploadFile = File(...),
  title: str = Form(""),
  published_date: date = Form(...),
  db: AsyncSession = Depends(get_db)
):
  temp_file_path = None

  try:
    # Save the uploaded file to a temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
      temp_file_path = temp_file.name
      shutil.copyfileobj(file.file, temp_file)
    
    # Upload the file to ImageKit
    upload_result = imagekit.upload_file(
      file=open(temp_file_path, "rb"),
      file_name=file.filename,
      options=UploadFileRequestOptions(
        use_unique_file_name=True,
        tags=["backend-upload", "news-thumbnail"]
      )
    )

    if upload_result.response_metadata.http_status_code == 200:
      # Create a news article with the uploaded image URL
      news_data = NewsCreate(
        title=title,
        image=upload_result.url,
        published_date=published_date
      )
      #news_data = NewsCreate(
      #  title="Title added manually",
      #  image="Image added manually",
      #  published_date=date(2025, 11, 27)
      #)
      # Convert the request schema (Pydantic) into a mapped SQLModel instance
      db_news = News(**news_data.model_dump())
      db.add(db_news)
      await db.commit()
      await db.refresh(db_news)
      return db_news
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Failed to upload image or create news: {str(e)}")
  finally:
    # Clean up the temporary file
    if temp_file_path and os.path.exists(temp_file_path):
      os.unlink(temp_file_path)
    file.file.close()

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

# ______________________________________________________
# Endpoints for NewsArticle model
# ______________________________________________________
@news_router.post("/news-article")
async def create_news_article(news_article: NewsArticleCreate, db: AsyncSession = Depends(get_db)) -> NewsArticle:
  db_news_article = NewsArticle(**news_article.model_dump())
  db.add(db_news_article)
  await db.commit()
  await db.refresh(db_news_article)
  return db_news_article


@news_router.get("/news-article/", response_model=List[NewsArticleRead], status_code=status.HTTP_200_OK)
async def get_news_articles(db: AsyncSession = Depends(get_db)):
  """ Get all news articles """
  result = await db.execute(select(NewsArticle).order_by(desc(NewsArticle.created_at)))
  news_articles = result.scalars().all()
  for article in news_articles:
    if not article.preview_text:
      article.preview_text = generate_excerpt(article.content)
  return news_articles