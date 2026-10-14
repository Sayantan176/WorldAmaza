from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class EventEvaluationResult(BaseModel):
    matches_watch: bool = Field(description="Whether this article genuinely matches the watch rules")
    relevance_score: float = Field(ge=0.0, le=1.0, description="Relevance score between 0.0 and 1.0")
    event_category: str = Field(description="Category of the event (contract, announcement, policy, confirmation, cancellation, launch, first_flight, vulnerability, other)")
    importance: str = Field(description="critical, high, medium, or low")
    evidence_status: str = Field(description="official_confirmed, multiple_sources, single_report, unverified_rumor, speculative")
    is_new_development: bool = Field(description="True if this is a genuine new development rather than rehashed old background")
    what_changed: str = Field(description="Precise description of what new fact, action, or decision occurred")
    headline: str = Field(description="Clear, grounded, professional headline for the detected event")
    summary: str = Field(description="Objective, concise summary strictly grounded in the article facts")
    match_rationale: str = Field(description="Why this event matched the specific watch rules")
    decision: str = Field(description="immediate_alert, digest_only, ignored, or flagged_review")
    dedup_topic_key: str = Field(description="Normalized short topic/entity key for grouping duplicate articles (e.g. tejas-mk1a-delivery-approval)")


class EventResponse(BaseModel):
    id: str
    dedup_key: str
    headline: str
    summary: str
    event_category: str
    importance: str
    evidence_status: str
    what_changed: str
    first_detected_at: datetime
    last_updated_at: datetime
    status: str

    model_config = {"from_attributes": True}
