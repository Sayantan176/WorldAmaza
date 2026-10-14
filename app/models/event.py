import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Boolean, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Event(Base):
    __tablename__ = "events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dedup_key = Column(String(128), unique=True, index=True, nullable=False)
    
    headline = Column(String(512), nullable=False)
    summary = Column(Text, nullable=False)
    event_category = Column(String(64), nullable=False, default="general")
    importance = Column(String(32), nullable=False, default="medium")  # critical, high, medium, low
    evidence_status = Column(String(64), nullable=False, default="single_report")  # official_confirmed, multiple_sources, single_report, unverified_rumor, speculative
    
    what_changed = Column(Text, nullable=False, default="")
    first_detected_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    status = Column(String(32), default="active", nullable=False)  # active, archived

    # Relationships
    supporting_articles = relationship("EventArticle", back_populates="event", cascade="all, delete-orphan")
    watch_matches = relationship("WatchMatch", back_populates="event", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="event", cascade="all, delete-orphan")


class EventArticle(Base):
    __tablename__ = "event_articles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = Column(String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    article_id = Column(String(36), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True)
    
    relevance_score = Column(Float, default=1.0, nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)
    added_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    event = relationship("Event", back_populates="supporting_articles")
    article = relationship("Article", back_populates="event_associations")

    __table_args__ = (
        Index("ix_event_articles_unique", "event_id", "article_id", unique=True),
    )
