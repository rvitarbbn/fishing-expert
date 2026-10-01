"""Forecast service for Open-Meteo marine API integration."""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import get_settings
from src.schemas.forecast import ForecastResponse, MarineVariables, WeatherVariables

logger = logging.getLogger(__name__)
settings = get_settings()


class ForecastCache:
    """Simple in-memory cache for forecast data."""

    def __init__(self, ttl_seconds: int = 3600):
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, tuple[datetime, dict[str, Any]]] = {}

    def _make_key(self, lat: float, lon: float, dt: datetime) -> str:
        """Create cache key from rounded coordinates and hour."""
        # Round to 0.1 degree for coordinate-based caching
        lat_rounded = round(lat, 1)
        lon_rounded = round(lon, 1)
        hour = dt.replace(minute=0, second=0, microsecond=0)
        return f"{lat_rounded}:{lon_rounded}:{hour.isoformat()}"

    def get(self, lat: float, lon: float, dt: datetime) -> Optional[dict[str, Any]]:
        """Get cached forecast if available and not expired."""
        key = self._make_key(lat, lon, dt)
        if key in self._cache:
            cached_time, data = self._cache[key]
            if datetime.utcnow() - cached_time < timedelta(seconds=self.ttl_seconds):
                logger.debug(f"Cache hit for {key}")
                return data
            else:
                del self._cache[key]
        return None

    def set(self, lat: float, lon: float, dt: datetime, data: dict[str, Any]) -> None:
        """Cache forecast data."""
        key = self._make_key(lat, lon, dt)
        self._cache[key] = (datetime.utcnow(), data)
        logger.debug(f"Cached forecast for {key}")


# ---------------------------------------------------------------------------
# Module-level singleton — shared across all requests / workers in the
# same process.  ``get_forecast_service()`` is the public accessor.
# ---------------------------------------------------------------------------
_forecast_service: Optional["ForecastService"] = None


def get_forecast_service() -> "ForecastService":
    """Return the process-wide ``ForecastService`` singleton."""
    global _forecast_service
    if _forecast_service is None:
        _forecast_service = ForecastService()
    return _forecast_service


class ForecastService:
    """
    Service for fetching marine and weather forecasts.
    
    Uses Open-Meteo Marine API with a process-wide in-memory cache.
    For multi-node deployments, swap ``ForecastCache`` for a Redis-backed
    implementation.
    """

    def __init__(self):
        self.base_url = settings.open_meteo_base_url
        self.cache = ForecastCache(ttl_seconds=settings.forecast_cache_ttl_seconds)
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def get_forecast(
        self,
        latitude: float,
        longitude: float,
        target_datetime: datetime,
    ) -> ForecastResponse:
        """
        Fetch marine and weather forecast for a location and time.
        
        Returns cached data if available.
        """
        # Check cache first
        cached = self.cache.get(latitude, longitude, target_datetime)
        if cached:
            return self._parse_cached_response(cached, latitude, longitude, target_datetime)

        # Fetch from API
        try:
            marine_data = await self._fetch_marine_forecast(latitude, longitude, target_datetime)
            weather_data = await self._fetch_weather_forecast(latitude, longitude, target_datetime)
            
            # Combine and cache
            combined = {
                "marine": marine_data,
                "weather": weather_data,
                "provider": "Open-Meteo",
                "provider_timestamp": datetime.utcnow().isoformat(),
                "fetch_timestamp": datetime.utcnow().isoformat(),
            }
            
            self.cache.set(latitude, longitude, target_datetime, combined)
            
            return self._build_response(combined, latitude, longitude, target_datetime)
            
        except Exception as e:
            logger.error(f"Forecast fetch failed: {e}")
            raise ForecastError(f"Failed to fetch forecast: {e}")

    async def _fetch_marine_forecast(
        self,
        latitude: float,
        longitude: float,
        target_datetime: datetime,
    ) -> dict[str, Any]:
        """Fetch marine forecast from Open-Meteo."""
        client = await self._get_client()
        
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "wave_height,wave_direction,wave_period,swell_wave_height,swell_wave_direction,swell_wave_period",
            "timezone": "auto",
        }
        
        response = await client.get(self.base_url, params=params)
        response.raise_for_status()
        
        data = response.json()
        return self._extract_hourly_data(data, target_datetime, "marine")

    async def _fetch_weather_forecast(
        self,
        latitude: float,
        longitude: float,
        target_datetime: datetime,
    ) -> dict[str, Any]:
        """Fetch weather forecast from Open-Meteo."""
        client = await self._get_client()
        
        # Use weather API for wind data
        weather_url = "https://api.open-meteo.com/v1/forecast"
        
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "wind_speed_10m,wind_direction_10m,wind_gusts_10m,temperature_2m,cloud_cover",
            "timezone": "auto",
        }
        
        response = await client.get(weather_url, params=params)
        response.raise_for_status()
        
        data = response.json()
        return self._extract_hourly_data(data, target_datetime, "weather")

    def _extract_hourly_data(
        self,
        data: dict[str, Any],
        target_datetime: datetime,
        data_type: str,
    ) -> dict[str, Any]:
        """Extract data for the target hour from hourly forecast."""
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        
        # Find closest hour
        target_hour = target_datetime.replace(minute=0, second=0, microsecond=0)
        target_str = target_hour.strftime("%Y-%m-%dT%H:%M")
        
        try:
            idx = times.index(target_str)
        except ValueError:
            # Find closest available time
            idx = 0
            for i, t in enumerate(times):
                if t <= target_str:
                    idx = i
        
        if data_type == "marine":
            return {
                "wave_height_m": self._safe_get(hourly, "wave_height", idx),
                "wave_direction": self._safe_get(hourly, "wave_direction", idx),
                "wave_period_s": self._safe_get(hourly, "wave_period", idx),
                "swell_height_m": self._safe_get(hourly, "swell_wave_height", idx),
                "swell_direction": self._safe_get(hourly, "swell_wave_direction", idx),
                "swell_period_s": self._safe_get(hourly, "swell_wave_period", idx),
            }
        else:
            return {
                "wind_speed_kmh": self._safe_get(hourly, "wind_speed_10m", idx),
                "wind_direction": self._safe_get(hourly, "wind_direction_10m", idx),
                "wind_gust_kmh": self._safe_get(hourly, "wind_gusts_10m", idx),
                "temperature_c": self._safe_get(hourly, "temperature_2m", idx),
                "cloud_cover_percent": self._safe_get(hourly, "cloud_cover", idx),
            }

    def _safe_get(
        self,
        data: dict[str, Any],
        key: str,
        idx: int,
    ) -> Optional[float]:
        """Safely get a value from hourly data."""
        values = data.get(key, [])
        if idx < len(values):
            return values[idx]
        return None

    def _build_response(
        self,
        data: dict[str, Any],
        latitude: float,
        longitude: float,
        target_datetime: datetime,
    ) -> ForecastResponse:
        """Build ForecastResponse from raw data."""
        marine = data.get("marine", {})
        weather = data.get("weather", {})
        
        return ForecastResponse(
            latitude=latitude,
            longitude=longitude,
            requested_datetime=target_datetime,
            forecast_datetime=target_datetime,
            marine=MarineVariables(
                wave_height_m=marine.get("wave_height_m"),
                wave_direction=marine.get("wave_direction"),
                wave_period_s=marine.get("wave_period_s"),
                swell_height_m=marine.get("swell_height_m"),
                swell_direction=marine.get("swell_direction"),
                swell_period_s=marine.get("swell_period_s"),
            ),
            weather=WeatherVariables(
                wind_speed_kmh=weather.get("wind_speed_kmh"),
                wind_direction=weather.get("wind_direction"),
                wind_gust_kmh=weather.get("wind_gust_kmh"),
                temperature_c=weather.get("temperature_c"),
                cloud_cover_percent=weather.get("cloud_cover_percent"),
            ),
            provider=data.get("provider", "Open-Meteo"),
            provider_timestamp=datetime.fromisoformat(data["provider_timestamp"]),
            fetch_timestamp=datetime.fromisoformat(data["fetch_timestamp"]),
            confidence=self._assess_confidence(marine, weather),
            warnings=[],
        )

    def _parse_cached_response(
        self,
        cached: dict[str, Any],
        latitude: float,
        longitude: float,
        target_datetime: datetime,
    ) -> ForecastResponse:
        """Parse cached data into ForecastResponse."""
        return self._build_response(cached, latitude, longitude, target_datetime)

    def _assess_confidence(
        self,
        marine: dict[str, Any],
        weather: dict[str, Any],
    ) -> str:
        """Assess forecast confidence based on data completeness."""
        marine_fields = ["wave_height_m", "wave_period_s"]
        weather_fields = ["wind_speed_kmh"]
        
        marine_complete = all(marine.get(f) is not None for f in marine_fields)
        weather_complete = all(weather.get(f) is not None for f in weather_fields)
        
        if marine_complete and weather_complete:
            return "high"
        elif marine_complete or weather_complete:
            return "medium"
        else:
            return "low"


class ForecastError(Exception):
    """Error fetching or processing forecast data."""
    pass
