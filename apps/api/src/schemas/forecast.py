"""Forecast schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ForecastRequest(BaseModel):
    """Request for marine forecast."""

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    target_datetime: datetime = Field(..., description="Target date and time")


class MarineVariables(BaseModel):
    """Marine forecast variables."""

    wave_height_m: Optional[float] = Field(None, description="Significant wave height")
    wave_direction: Optional[int] = Field(None, description="Wave direction in degrees")
    wave_period_s: Optional[float] = Field(None, description="Wave period in seconds")
    swell_height_m: Optional[float] = Field(None, description="Swell height")
    swell_direction: Optional[int] = Field(None, description="Swell direction in degrees")
    swell_period_s: Optional[float] = Field(None, description="Swell period in seconds")
    sea_surface_temp_c: Optional[float] = Field(None, description="Sea surface temperature")


class WeatherVariables(BaseModel):
    """Weather forecast variables."""

    wind_speed_kmh: Optional[float] = Field(None, description="Wind speed")
    wind_direction: Optional[int] = Field(None, description="Wind direction in degrees")
    wind_gust_kmh: Optional[float] = Field(None, description="Wind gust speed")
    temperature_c: Optional[float] = Field(None, description="Air temperature")
    cloud_cover_percent: Optional[int] = Field(None, description="Cloud cover percentage")


class ForecastResponse(BaseModel):
    """Marine and weather forecast response."""

    latitude: float
    longitude: float
    requested_datetime: datetime
    forecast_datetime: datetime = Field(..., description="Actual forecast time (may differ)")
    marine: MarineVariables
    weather: WeatherVariables
    provider: str = Field(..., description="Forecast provider name")
    provider_timestamp: datetime = Field(..., description="When provider generated forecast")
    fetch_timestamp: datetime = Field(..., description="When we fetched the forecast")
    confidence: str = Field(..., description="Confidence level: high, medium, low")
    warnings: list[str] = Field(default_factory=list, description="Any forecast warnings")
    ims_verification_url: str = Field(
        default="https://ims.gov.il/en/meditSea",
        description="Israel Meteorological Service verification link",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "latitude": 32.0,
                "longitude": 34.8,
                "requested_datetime": "2026-10-01T18:00:00Z",
                "forecast_datetime": "2026-10-01T18:00:00Z",
                "marine": {
                    "wave_height_m": 0.8,
                    "wave_direction": 270,
                    "wave_period_s": 6.5,
                },
                "weather": {
                    "wind_speed_kmh": 15,
                    "wind_direction": 270,
                },
                "provider": "Open-Meteo",
                "provider_timestamp": "2026-10-01T12:00:00Z",
                "fetch_timestamp": "2026-10-01T15:30:00Z",
                "confidence": "medium",
                "warnings": [],
                "ims_verification_url": "https://ims.gov.il/en/meditSea",
            }
        }
