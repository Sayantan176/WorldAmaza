import json
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Watch(Base):
    __tablename__ = "watches"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)  # original user prompt
    structured_rules = Column(Text, nullable=False, default="{}")  # JSON encoded rules
    
    status = Column(String(32), default="active", nullable=False, index=True)  # active, paused, archived
    delivery_mode = Column(String(32), default="immediate", nullable=False)  # immediate, daily_digest, weekly_digest, both
    polling_interval_minutes = Column(Integer, default=30, nullable=False)
    
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    last_matched_at = Column(DateTime(timezone=True), nullable=True)
    events_count = Column(Integer, default=0, nullable=False)
    last_error = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    user = relationship("User", back_populates="watches")
    matches = relationship("WatchMatch", back_populates="watch", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="watch", cascade="all, delete-orphan")
    feedbacks = relationship("Feedback", back_populates="watch", cascade="all, delete-orphan")
    monitoring_runs = relationship("MonitoringRun", back_populates="watch")

    @property
    def rules_dict(self) -> dict:
        try:
            return json.loads(self.structured_rules)
        except Exception:
            return {}

    def set_rules_dict(self, data: dict):
        self.structured_rules = json.dumps(data)
