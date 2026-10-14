from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: str
    user_id: str
    watch_id: str
    event_id: str
    is_read: bool
    delivery_channel: str
    email_sent: bool
    email_status: str
    email_error: Optional[str] = None
    created_at: datetime
    
    # Nested event summary fields for client convenience
    event_headline: Optional[str] = None
    event_summary: Optional[str] = None
    event_importance: Optional[str] = None
    event_evidence_status: Optional[str] = None
    watch_title: Optional[str] = None
    source_name: Optional[str] = None
    source_url: Optional[str] = None

    model_config = {"from_attributes": True}


class NotificationUpdate(BaseModel):
    is_read: bool
