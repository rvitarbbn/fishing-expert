"""Pydantic schemas for API request/response validation."""

from src.schemas.recommendation import (
    AlternativeRecommendation,
    Conditions,
    DataQuality,
    Equipment,
    Location,
    LureRecommendation,
    Observations,
    RecommendationRequest,
    RecommendationResponse,
)
from src.schemas.catalog import FishSpecies, Lure, RetrieveMethod, ColorFamily
from src.schemas.feedback import FeedbackRequest, FeedbackResponse
from src.schemas.forecast import ForecastRequest, ForecastResponse

__all__ = [
    "RecommendationRequest",
    "RecommendationResponse",
    "LureRecommendation",
    "AlternativeRecommendation",
    "Location",
    "Conditions",
    "Observations",
    "Equipment",
    "DataQuality",
    "FishSpecies",
    "Lure",
    "RetrieveMethod",
    "ColorFamily",
    "FeedbackRequest",
    "FeedbackResponse",
    "ForecastRequest",
    "ForecastResponse",
]
