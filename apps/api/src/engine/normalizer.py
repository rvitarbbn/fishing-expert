"""Input normalization service."""

import logging
from datetime import datetime
from typing import Any, Optional

from src.schemas.recommendation import Conditions, Observations, RecommendationRequest

logger = logging.getLogger(__name__)


class Normalizer:
    """Normalizes raw inputs into categorical conditions for rule evaluation."""

    def __init__(self, known_fish_ids: set[str] | None = None):
        # When provided, used to validate / normalize ``target_fish``
        self._known_fish_ids: set[str] = known_fish_ids or set()

    # Sea state thresholds (configurable)
    SEA_STATE_THRESHOLDS = {
        "flat": (0, 0.25),
        "calm": (0.25, 0.50),
        "light_chop": (0.50, 0.80),
        "moderate": (0.80, 1.20),
        "working": (1.20, 1.50),
        "rough": (1.50, float("inf")),
    }

    # Wind strength thresholds (km/h)
    WIND_THRESHOLDS = {
        "calm": (0, 10),
        "light": (10, 20),
        "moderate": (20, 35),
        "strong": (35, float("inf")),
    }

    # Time bucket definitions
    TIME_BUCKETS = {
        "night": (0, 5),
        "dawn": (5, 6),
        "sunrise": (6, 8),
        "morning": (8, 12),
        "midday": (12, 16),
        "afternoon": (16, 18),
        "sunset": (18, 20),
        "dusk": (20, 21),
    }

    def normalize(
        self,
        request: RecommendationRequest,
        forecast: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Normalize request inputs into categorical conditions.
        
        User observations override forecast values for:
        - water_clarity
        - foam
        - surface_activity
        """
        # Validate target_fish — normalize unrecognized values to "unknown"
        target_fish = request.target_fish
        target_fish_recognized = True
        if self._known_fish_ids and target_fish not in self._known_fish_ids and target_fish != "unknown":
            logger.warning(
                "Unrecognized target_fish '%s' — normalizing to 'unknown'", target_fish
            )
            target_fish_recognized = False
            target_fish = "unknown"

        normalized: dict[str, Any] = {
            "target_fish": target_fish,
            "target_fish_recognized": target_fish_recognized,
            "location_name": request.location.name,
            "structure": request.location.structure,
            "rod_cast_min_g": request.equipment.rod_cast_min_g,
            "rod_cast_max_g": request.equipment.rod_cast_max_g,
        }

        # Derive time bucket
        normalized["time_bucket"] = self._derive_time_bucket(request.fishing_time)
        normalized["fishing_datetime"] = request.fishing_time.isoformat()

        # Merge conditions from request and forecast
        conditions = self._merge_conditions(request.conditions, forecast)
        
        # Derive sea state from wave height
        if conditions.get("wave_height_m") is not None:
            normalized["sea_state"] = self._derive_sea_state(conditions["wave_height_m"])
            normalized["wave_height_m"] = conditions["wave_height_m"]

        # Derive wind strength
        if conditions.get("wind_speed_kmh") is not None:
            normalized["wind_strength"] = self._derive_wind_strength(conditions["wind_speed_kmh"])
            normalized["wind_speed_kmh"] = conditions["wind_speed_kmh"]

        # Copy other conditions
        for key in ["water_clarity", "current_strength", "desired_layer", "sea_state"]:
            if conditions.get(key):
                normalized[key] = conditions[key]

        # Process observations (override forecast)
        if request.observations:
            obs = request.observations
            if obs.foam is not None:
                normalized["foam"] = obs.foam
            if obs.surface_activity is not None:
                normalized["surface_activity"] = obs.surface_activity
            if obs.birds_diving is not None:
                normalized["birds_diving"] = obs.birds_diving
            if obs.activity_distance is not None:
                normalized["activity_distance"] = obs.activity_distance
            if obs.baitfish_visible is not None:
                normalized["baitfish_visible"] = obs.baitfish_visible

        # Equipment details
        if request.equipment.reel_size:
            normalized["reel_size"] = request.equipment.reel_size
        if request.equipment.main_line_pe:
            normalized["main_line_pe"] = request.equipment.main_line_pe
        if request.equipment.leader_mm:
            normalized["leader_mm"] = request.equipment.leader_mm

        return normalized

    def _derive_time_bucket(self, dt: datetime) -> str:
        """Derive time bucket from datetime."""
        hour = dt.hour
        
        # Night spans midnight
        if hour >= 21 or hour < 5:
            return "night"
        
        for bucket, (start, end) in self.TIME_BUCKETS.items():
            if start <= hour < end:
                return bucket
        
        return "midday"  # Default fallback

    def _derive_sea_state(self, wave_height_m: float) -> str:
        """Derive categorical sea state from wave height."""
        for state, (min_h, max_h) in self.SEA_STATE_THRESHOLDS.items():
            if min_h <= wave_height_m < max_h:
                return state
        return "rough"

    def _derive_wind_strength(self, wind_speed_kmh: float) -> str:
        """Derive categorical wind strength from wind speed."""
        for strength, (min_s, max_s) in self.WIND_THRESHOLDS.items():
            if min_s <= wind_speed_kmh < max_s:
                return strength
        return "strong"

    def _merge_conditions(
        self,
        request_conditions: Optional[Conditions],
        forecast: Optional[dict[str, Any]],
    ) -> dict[str, Any]:
        """Merge request conditions with forecast, request takes precedence."""
        merged: dict[str, Any] = {}

        # Start with forecast if available
        if forecast:
            if forecast.get("marine"):
                marine = forecast["marine"]
                if marine.get("wave_height_m") is not None:
                    merged["wave_height_m"] = marine["wave_height_m"]
                if marine.get("wave_period_s") is not None:
                    merged["wave_period_s"] = marine["wave_period_s"]
                if marine.get("swell_height_m") is not None:
                    merged["swell_height_m"] = marine["swell_height_m"]
            
            if forecast.get("weather"):
                weather = forecast["weather"]
                if weather.get("wind_speed_kmh") is not None:
                    merged["wind_speed_kmh"] = weather["wind_speed_kmh"]
                if weather.get("wind_gust_kmh") is not None:
                    merged["wind_gust_kmh"] = weather["wind_gust_kmh"]

        # Override with request conditions
        if request_conditions:
            if request_conditions.wave_height_m is not None:
                merged["wave_height_m"] = request_conditions.wave_height_m
            if request_conditions.wave_period_s is not None:
                merged["wave_period_s"] = request_conditions.wave_period_s
            if request_conditions.wind_speed_kmh is not None:
                merged["wind_speed_kmh"] = request_conditions.wind_speed_kmh
            if request_conditions.water_clarity is not None:
                merged["water_clarity"] = request_conditions.water_clarity
            if request_conditions.sea_state is not None:
                merged["sea_state"] = request_conditions.sea_state
            if request_conditions.current_strength is not None:
                merged["current_strength"] = request_conditions.current_strength
            if request_conditions.desired_layer is not None:
                merged["desired_layer"] = request_conditions.desired_layer

        return merged

    def calculate_completeness(self, normalized: dict[str, Any]) -> float:
        """
        Calculate completeness score based on decision-changing fields.
        
        Weights reflect impact on recommendation quality.
        """
        weights = {
            "target_fish": 0.15,
            "rod_cast_max_g": 0.15,
            "time_bucket": 0.10,
            "sea_state": 0.10,
            "water_clarity": 0.10,
            "structure": 0.08,
            "wind_strength": 0.08,
            "foam": 0.06,
            "surface_activity": 0.06,
            "current_strength": 0.05,
            "desired_layer": 0.05,
            "birds_diving": 0.02,
        }

        total_weight = sum(weights.values())
        present_weight = sum(
            weight for field, weight in weights.items()
            if normalized.get(field) is not None
        )

        return present_weight / total_weight
