import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True)
    supabase_user_id = Column(String(255), unique=True, index=True, nullable=True)
    
    full_name = Column(String(255), nullable=True)
    timezone = Column(String(64), default="UTC", nullable=False)
    email_notifications_enabled = Column(Boolean, default=True, nullable=False)
    digest_frequency = Column(String(32), default="daily", nullable=False)  # daily, weekly, none
    digest_time = Column(String(8), default="08:00", nullable=False)  # HH:MM local
    
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    watches = relationship("Watch", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    digests = relationship("Digest", back_populates="user", cascade="all, delete-orphan")
    feedbacks = relationship("Feedback", back_populates="user", cascade="all, delete-orphan")
