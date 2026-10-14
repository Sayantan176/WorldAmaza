from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class DigestResponse(BaseModel):
    id: str
    user_id: str
    title: str
    period: str
    event_count: int
    content: str
    email_sent: bool
    email_status: str
    email_error: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DigestGenerateRequest(BaseModel):
    period: Optional[str] = "daily"  # daily or weekly
