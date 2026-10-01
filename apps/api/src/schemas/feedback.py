"""Feedback schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    """User feedback on a recommendation."""

    recommendation_id: str = Field(..., description="ID of the recommendation")
    recommendation_followed: bool = Field(
        ..., description="Whether the user followed the recommendation"
    )
    lure_used: Optional[str] = Field(None, description="Actual lure type used")
    strike_seen: Optional[bool] = Field(None, description="Whether a strike was observed")
    fish_caught: Optional[bool] = Field(None, description="Whether a fish was caught")
    species_reported: Optional[str] = Field(None, description="Species caught if any")
    free_text: Optional[str] = Field(
        None, max_length=1000, description="Free text feedback"
    )
    consent_to_research: bool = Field(
        False, description="Whether user consents to research use"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "recommendation_id": "rec_abc123",
                "recommendation_followed": True,
                "lure_used": "minnow",
                "strike_seen": True,
                "fish_caught": True,
                "species_reported": "european_seabass",
                "consent_to_research": True,
            }
        }


class FeedbackResponse(BaseModel):
    """Response after submitting feedback."""

    feedback_id: str = Field(..., description="Unique feedback ID")
    recommendation_id: str = Field(..., description="Associated recommendation ID")
    received_at: datetime = Field(..., description="When feedback was received")
    message: str = Field(default="Feedback received successfully")
