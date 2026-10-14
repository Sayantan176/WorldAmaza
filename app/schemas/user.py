from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    timezone: Optional[str] = "UTC"


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserSettingsUpdate(BaseModel):
    full_name: Optional[str] = None
    timezone: Optional[str] = None
    email_notifications_enabled: Optional[bool] = None
    digest_frequency: Optional[Literal["daily", "weekly", "none"]] = None
    digest_time: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    timezone: str
    email_notifications_enabled: bool
    digest_frequency: str
    digest_time: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
