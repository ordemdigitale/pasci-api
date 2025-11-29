# app/services/imagekit_service.py
from imagekitio import ImageKit
from dotenv import load_dotenv
import os

load_dotenv()

# Retrieve credentials from environment variables
imagekit = ImageKit(
  private_key=os.getenv("IMAGEKIT_PRIVATE_KEY"),
  public_key=os.getenv("IMAGEKIT_PUBLIC_KEY"),
  url_endpoint=os.getenv("IMAGEKIT_URL")
)