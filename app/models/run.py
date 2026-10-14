import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class MonitoringRun(Base):
    __tablename__ = "monitoring_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    watch_id = Column(String(36), ForeignKey("watches.id", ondelete="SET NULL"), nullable=True, index=True)
    
    trigger_type = Column(String(32), default="scheduled", nullable=False)  # scheduled, manual, batch
    status = Column(String(32), default="running", nullable=False)  # running, success, failed, no_updates
    
    articles_fetched = Column(Integer, default=0, nullable=False)
    articles_evaluated = Column(Integer, default=0, nullable=False)
    events_matched = Column(Integer, default=0, nullable=False)
    notifications_created = Column(Integer, default=0, nullable=False)
    
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    watch = relationship("Watch", back_populates="monitoring_runs")
