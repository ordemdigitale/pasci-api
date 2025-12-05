# app/services/imagekit_service.py
from imagekitio import ImageKit
from dotenv import load_dotenv
#import os
from app.core.config import settings

load_dotenv()

# Retrieve credentials from environment variables
imagekit = ImageKit(
  private_key=settings.IMAGEKIT_PRIVATE_KEY,
  public_key=settings.IMAGEKIT_PUBLIC_KEY,
  url_endpoint=settings.IMAGEKIT_URL,
)