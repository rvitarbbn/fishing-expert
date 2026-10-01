"""Pydantic schemas for API request/response validation."""

from src.schemas.recommendation import (
    AlternativeRecommendation,
    Conditions,
    DataQuality,
    Equipment,
    EquipmentCompatibility,
    Location,
    LureRecommendation,
    NormalizedConditions,
    Observations,
    RecommendationRequest,
    RecommendationResponse,
)
from src.schemas.catalog import (
    ColorFamily,
    FishSpecies,
    LocationSeed,
    Lure,
    RetrieveMethod,
    SeedStatus,
)
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
    "EquipmentCompatibility",
    "NormalizedConditions",
    "FishSpecies",
    "Lure",
    "RetrieveMethod",
    "ColorFamily",
    "LocationSeed",
    "SeedStatus",
    "FeedbackRequest",
    "FeedbackResponse",
    "ForecastRequest",
    "ForecastResponse",
]
