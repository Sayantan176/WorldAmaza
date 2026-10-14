import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class WatchMatch(Base):
    __tablename__ = "watch_matches"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    watch_id = Column(String(36), ForeignKey("watches.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id = Column(String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    
    relevance_score = Column(Float, default=0.0, nullable=False)
    match_rationale = Column(Text, nullable=False)
    decision = Column(String(32), default="immediate_alert", nullable=False)  # immediate_alert, digest_only, ignored, flagged_review
    
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    watch = relationship("Watch", back_populates="matches")
    event = relationship("Event", back_populates="watch_matches")

    __table_args__ = (
        Index("ix_watch_matches_unique", "watch_id", "event_id", unique=True),
    )
