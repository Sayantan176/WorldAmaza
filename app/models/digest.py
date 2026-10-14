import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Digest(Base):
    __tablename__ = "digests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    title = Column(String(255), nullable=False)
    period = Column(String(32), default="daily", nullable=False)  # daily, weekly
    event_count = Column(Integer, default=0, nullable=False)
    content = Column(Text, nullable=False)  # JSON or formatted digest content
    
    email_sent = Column(Boolean, default=False, nullable=False)
    email_status = Column(String(32), default="pending", nullable=False)  # pending, delivered, failed, skipped
    email_error = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="digests")
