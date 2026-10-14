import json
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Index
from sqlalchemy.orm import relationship
from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Article(Base):
    __tablename__ = "articles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    canonical_url = Column(String(2048), nullable=False, index=True)
    title = Column(String(512), nullable=False)
    source_name = Column(String(255), nullable=False)
    author = Column(String(255), nullable=True)
    
    published_at = Column(DateTime(timezone=True), nullable=True)
    retrieved_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    
    snippet = Column(Text, nullable=False, default="")
    content = Column(Text, nullable=True)
    content_hash = Column(String(64), nullable=False, index=True)
    
    source_type = Column(String(32), default="gnews", nullable=False)  # gnews, rss
    language = Column(String(16), default="en", nullable=False)
    source_metadata = Column(Text, nullable=False, default="{}")

    # Relationships
    event_associations = relationship("EventArticle", back_populates="article", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_articles_url_hash", "canonical_url", "content_hash"),
    )

    @property
    def metadata_dict(self) -> dict:
        try:
            return json.loads(self.source_metadata)
        except Exception:
            return {}
