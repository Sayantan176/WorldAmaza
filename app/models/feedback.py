import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    watch_id = Column(String(36), ForeignKey("watches.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id = Column(String(36), ForeignKey("events.id", ondelete="SET NULL"), nullable=True, index=True)
    notification_id = Column(String(36), ForeignKey("notifications.id", ondelete="SET NULL"), nullable=True, index=True)
    
    feedback_type = Column(String(32), nullable=False)  # relevant, irrelevant, too_trivial, already_reported
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    user = relationship("User", back_populates="feedbacks")
    watch = relationship("Watch", back_populates="feedbacks")
    notification = relationship("Notification", back_populates="feedbacks")
