"""Public chat-widget API shapes (unauthenticated — the lead-facing surface)."""
from pydantic import BaseModel, Field


class WidgetSessionCreate(BaseModel):
    # Ad attribution — where the click came from (e.g. "facebook_ad_july",
    # "google_search", "telegram"). Stored on the lead for traction reporting.
    ad_source: str | None = Field(default=None, max_length=255)


class WidgetSessionRead(BaseModel):
    lead_id: int
    conversation_id: int
    greeting: str


class WidgetMessageRequest(BaseModel):
    conversation_id: int
    message: str = Field(..., min_length=1, max_length=2000)


class WidgetMessageResponse(BaseModel):
    reply: str
