from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone

class NewsArticleCreate(BaseModel):
    title: str
    content: str
    author: str
    category: str
    image_url: Optional[str] = None
    status: str = "pending"

class NewsArticleDB(NewsArticleCreate):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class NewsArticleResponse(NewsArticleDB):
    id: str

# Authentication Models
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

class UserInDB(BaseModel):
    username: str
    hashed_password: str
    role: str
