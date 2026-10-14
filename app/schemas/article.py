from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ArticleNormalized(BaseModel):
    canonical_url: str
    title: str
    source_name: str
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    snippet: str = ""
    content: Optional[str] = None
    content_hash: str
    source_type: str = "gnews"  # gnews, rss
    language: str = "en"
    source_metadata: Dict[str, Any] = Field(default_factory=dict)
