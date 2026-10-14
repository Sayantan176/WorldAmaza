from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class StructuredWatchRules(BaseModel):
    title: str = Field(..., description="Short, concise, human-readable name of the watch")
    description: str = Field(..., description="Original user request prompt")
    subjects: List[str] = Field(default_factory=list, description="Entities, organizations, locations, programs, technologies, or topics to track")
    include_terms: List[str] = Field(default_factory=list, description="Useful search keywords for news retrieval")
    exclude_terms: List[str] = Field(default_factory=list, description="Explicitly excluded topics, keywords, or noise to ignore")
    trigger_conditions: List[str] = Field(default_factory=list, description="Specific developments or criteria that should trigger notifications")
    event_categories: List[str] = Field(
        default_factory=lambda: ["announcement", "confirmation", "policy"],
        description="Event categories, e.g., contract, announcement, policy, confirmation, cancellation, launch, first_flight, vulnerability"
    )
    importance_threshold: Literal["critical", "high", "medium", "low"] = Field(
        default="medium",
        description="Minimum importance required to notify"
    )
    evidence_requirement: Literal["official_confirmation", "multiple_sources", "any_report"] = Field(
        default="any_report",
        description="Required strength of evidence"
    )
    uncertainty_policy: Literal["suppress", "flag_unverified", "allow"] = Field(
        default="flag_unverified",
        description="Handling of unverified or conflicting claims"
    )
    immediate_alert_conditions: List[str] = Field(
        default_factory=list,
        description="Conditions that qualify for immediate alert"
    )
    digest_only_conditions: List[str] = Field(
        default_factory=list,
        description="Conditions that should only be grouped in digests"
    )
    delivery_mode: Literal["immediate", "daily_digest", "weekly_digest", "both"] = Field(
        default="immediate",
        description="Preferred delivery channel / timing"
    )
    digest_time: str = Field(default="08:00", description="Preferred local time for digest (HH:MM)")
    timezone: str = Field(default="UTC", description="IANA timezone identifier")
    polling_interval: int = Field(default=30, description="Server polling interval in minutes")
    status: Literal["active", "paused", "archived"] = Field(default="active", description="Watch operational status")


class WatchPromptRequest(BaseModel):
    prompt: str = Field(..., min_length=5, max_length=2000, description="Natural language monitoring prompt")


class WatchCreateRequest(BaseModel):
    title: str
    description: str
    rules: StructuredWatchRules
    delivery_mode: Optional[Literal["immediate", "daily_digest", "weekly_digest", "both"]] = "immediate"
    polling_interval: Optional[int] = 30


class WatchUpdateRequest(BaseModel):
    title: Optional[str] = None
    status: Optional[Literal["active", "paused", "archived"]] = None
    delivery_mode: Optional[Literal["immediate", "daily_digest", "weekly_digest", "both"]] = None
    polling_interval_minutes: Optional[int] = None
    rules: Optional[StructuredWatchRules] = None


class WatchResponse(BaseModel):
    id: str
    user_id: str
    title: str
    description: str
    structured_rules: dict
    status: str
    delivery_mode: str
    polling_interval_minutes: int
    last_checked_at: Optional[datetime] = None
    last_matched_at: Optional[datetime] = None
    events_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
