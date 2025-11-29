import sqlalchemy.dialects.postgresql as pg
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Integer, String
from sqlalchemy.sql.expression import text
from datetime import datetime



class Post(SQLModel, table=True):
  id: int = Field(default=None, primary_key=True)
  title: str = Field(nullable=False)
  content: str = Field(nullable=True)
  created_at: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.now))
  updated_at: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.now))