"""Recommendation request and response schemas."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class Location(BaseModel):
    """Location information for fishing recommendation."""

    name: str = Field(..., description="Location name")
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    structure: Optional[str] = Field(
        None,
        description="Structure type: reef, sandy, rocky, breakwater, mixed, etc.",
    )


class Conditions(BaseModel):
    """Marine and weather conditions."""

    wave_height_m: Optional[float] = Field(None, ge=0, description="Wave height in meters")
    wave_direction: Optional[str] = None
    wave_period_s: Optional[float] = Field(None, ge=0, description="Wave period in seconds")
    swell_height_m: Optional[float] = Field(None, ge=0)
    swell_direction: Optional[str] = None
    swell_period_s: Optional[float] = Field(None, ge=0)
    wind_speed_kmh: Optional[float] = Field(None, ge=0)
    wind_direction: Optional[str] = None
    wind_gust_kmh: Optional[float] = Field(None, ge=0)
    water_clarity: Optional[str] = Field(
        None, description="clear, slightly_murky, murky"
    )
    sea_state: Optional[str] = Field(
        None, description="flat, calm, light_chop, moderate, working, rough"
    )
    current_strength: Optional[str] = Field(None, description="weak, moderate, strong")
    desired_layer: Optional[str] = Field(
        None, description="surface, shallow, midwater, bottom"
    )


class Observations(BaseModel):
    """User observations at the fishing location."""

    foam: Optional[bool] = Field(None, description="Foam present in water")
    baitfish_visible: Optional[bool] = None
    birds_diving: Optional[bool] = None
    surface_activity: Optional[bool] = Field(None, description="Fish activity at surface")
    activity_distance: Optional[str] = Field(None, description="near, medium, far")
    estimated_depth_m: Optional[float] = Field(None, ge=0)


class Equipment(BaseModel):
    """Fishing equipment specifications."""

    rod_cast_min_g: float = Field(..., ge=0, description="Minimum casting weight in grams")
    rod_cast_max_g: float = Field(..., gt=0, description="Maximum casting weight in grams")
    reel_size: Optional[int] = Field(None, ge=1000, le=10000)
    main_line_pe: Optional[float] = Field(None, ge=0.3, le=6.0)
    leader_mm: Optional[float] = Field(None, ge=0.1, le=1.0)

    @field_validator("rod_cast_max_g")
    @classmethod
    def max_must_exceed_min(cls, v: float, info: Any) -> float:
        """Validate that max exceeds min."""
        if "rod_cast_min_g" in info.data and v <= info.data["rod_cast_min_g"]:
            raise ValueError("rod_cast_max_g must be greater than rod_cast_min_g")
        return v


class RecommendationRequest(BaseModel):
    """Request for lure recommendation."""

    target_fish: str = Field(..., description="Target fish species ID or 'unknown'")
    fishing_time: datetime = Field(..., description="Date and time of fishing")
    location: Location
    use_forecast: bool = Field(True, description="Whether to fetch forecast data")
    conditions: Optional[Conditions] = None
    observations: Optional[Observations] = None
    equipment: Equipment

    class Config:
        json_schema_extra = {
            "example": {
                "target_fish": "european_seabass",
                "fishing_time": "2026-10-01T18:00:00",
                "location": {"name": "Palmachim", "structure": "mixed"},
                "equipment": {"rod_cast_min_g": 10, "rod_cast_max_g": 40},
            }
        }


class LureRecommendation(BaseModel):
    """A single lure recommendation."""

    lure_type: str = Field(..., description="Lure type ID")
    lure_name_he: str = Field(..., description="Hebrew name")
    length_cm_range: tuple[float, float] = Field(..., description="Recommended length range")
    weight_g_range: tuple[float, float] = Field(..., description="Recommended weight range")
    recommended_weight_g: float = Field(..., description="Specific recommended weight")
    color_family: str = Field(..., description="Recommended color family")
    working_layer: str = Field(..., description="Target water layer")
    retrieve_method: str = Field(..., description="Retrieve method ID")
    retrieve_steps_he: list[str] = Field(..., description="Retrieve steps in Hebrew")
    suitability_score: int = Field(
        ..., ge=0, le=100, description="Rules-based suitability score (NOT catch probability)"
    )
    contributing_rule_ids: list[str] = Field(..., description="Rule IDs that contributed to score")


class AlternativeRecommendation(BaseModel):
    """Alternative recommendation with switch condition."""

    recommendation: LureRecommendation
    switch_condition_he: str = Field(..., description="When to switch to this alternative")


class DataQuality(BaseModel):
    """Data quality and completeness information."""

    completeness_score: float = Field(..., ge=0, le=1, description="Proportion of fields present")
    forecast_confidence: Optional[str] = Field(None, description="Forecast confidence level")
    forecast_timestamp: Optional[datetime] = None
    forecast_provider: Optional[str] = None
    data_source: str = Field(..., description="user_supplied, forecast, or mixed")


class RecommendationResponse(BaseModel):
    """Response containing lure recommendations."""

    recommendation_id: str = Field(..., description="Unique recommendation ID")
    request_timestamp: datetime
    primary: LureRecommendation
    alternatives: list[AlternativeRecommendation] = Field(
        ..., max_length=2, description="Up to 2 alternative recommendations"
    )
    normalized_conditions: dict[str, Any] = Field(
        ..., description="Normalized conditions used for recommendation"
    )
    reasons: list[str] = Field(..., description="Reasons for the recommendation in Hebrew")
    warnings: list[str] = Field(default_factory=list, description="Safety and legal warnings")
    missing_information: list[str] = Field(
        default_factory=list, description="Information that could improve recommendation"
    )
    equipment_compatibility: dict[str, Any] = Field(
        ..., description="Equipment compatibility assessment"
    )
    data_quality: DataQuality
    rules_version: str = Field(..., description="Version of the rules used")
    knowledge_version: str = Field(..., description="Version of the knowledge base used")

    class Config:
        json_schema_extra = {
            "example": {
                "recommendation_id": "rec_abc123",
                "request_timestamp": "2026-10-01T18:00:00Z",
                "primary": {
                    "lure_type": "minnow",
                    "lure_name_he": "מינו",
                    "length_cm_range": [9, 12],
                    "weight_g_range": [12, 25],
                    "recommended_weight_g": 18,
                    "color_family": "natural_sardine",
                    "working_layer": "shallow",
                    "retrieve_method": "slow_pause",
                    "retrieve_steps_he": [
                        "גלגל לאט 3-6 סיבובים",
                        "עצור 1-3 שניות",
                    ],
                    "suitability_score": 78,
                    "contributing_rule_ids": ["BASE_european_seabass_minnow", "COND_001_minnow"],
                },
                "alternatives": [],
                "normalized_conditions": {"sea_state": "moderate", "time_bucket": "sunset"},
                "reasons": ["מינו מתאים ללברק בתנאי קצף"],
                "warnings": [],
                "missing_information": ["water_clarity"],
                "equipment_compatibility": {"weight_within_range": True},
                "data_quality": {
                    "completeness_score": 0.75,
                    "data_source": "user_supplied",
                },
                "rules_version": "1.0.0",
                "knowledge_version": "1.0.0",
            }
        }
