"""Forecast API router."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from src.schemas.forecast import ForecastResponse
from src.services.forecast import ForecastError, ForecastService

router = APIRouter()


@router.get("/forecast", response_model=ForecastResponse)
async def get_forecast(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude"),
    datetime_str: str = Query(
        ...,
        alias="datetime",
        description="Target datetime in ISO format",
    ),
) -> ForecastResponse:
    """
    Get marine and weather forecast for a location and time.
    
    Uses Open-Meteo API with caching. Includes provider metadata
    and fetch timestamp for transparency.
    
    Note: Coastal current/tide accuracy is limited. Always verify
    with official Israel Meteorological Service forecast.
    """
    try:
        target_dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid datetime format. Use ISO format (e.g., 2026-10-01T18:00:00)",
        )
    
    service = ForecastService()
    
    try:
        response = await service.get_forecast(
            latitude=latitude,
            longitude=longitude,
            target_datetime=target_dt,
        )
        return response
    except ForecastError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Forecast service unavailable: {e}",
        )
