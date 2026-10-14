import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    watch_id = Column(String(36), ForeignKey("watches.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id = Column(String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    delivery_channel = Column(String(32), default="both", nullable=False)  # in_app, email, both
    email_sent = Column(Boolean, default=False, nullable=False)
    email_status = Column(String(32), default="pending", nullable=False)  # pending, delivered, failed, skipped
    email_error = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="notifications")
    watch = relationship("Watch", back_populates="notifications")
    event = relationship("Event", back_populates="notifications")
    feedbacks = relationship("Feedback", back_populates="notification", cascade="all, delete-orphan")
