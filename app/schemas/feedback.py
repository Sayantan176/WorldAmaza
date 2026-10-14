from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field


class FeedbackCreateRequest(BaseModel):
    watch_id: str
    event_id: Optional[str] = None
    notification_id: Optional[str] = None
    feedback_type: Literal["relevant", "irrelevant", "too_trivial", "already_reported"]
    comment: Optional[str] = Field(None, max_length=500)


class FeedbackResponse(BaseModel):
    id: str
    user_id: str
    watch_id: str
    event_id: Optional[str]
    notification_id: Optional[str]
    feedback_type: str
    comment: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
