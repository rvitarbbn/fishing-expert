"""Tests for the input normalizer."""

from datetime import datetime

import pytest

from src.engine.normalizer import Normalizer
from src.schemas.recommendation import (
    Conditions,
    Equipment,
    Location,
    Observations,
    RecommendationRequest,
)


@pytest.fixture
def normalizer():
    return Normalizer()


@pytest.fixture
def base_request():
    return RecommendationRequest(
        target_fish="european_seabass",
        fishing_time=datetime(2026, 10, 1, 18, 0),
        location=Location(name="Palmachim", structure="mixed"),
        equipment=Equipment(rod_cast_min_g=10, rod_cast_max_g=40),
    )


class TestTimeBucket:
    def test_night_early(self, normalizer, base_request):
        base_request.fishing_time = datetime(2026, 10, 1, 3, 0)
        result = normalizer.normalize(base_request)
        assert result["time_bucket"] == "night"

    def test_night_late(self, normalizer, base_request):
        base_request.fishing_time = datetime(2026, 10, 1, 22, 0)
        result = normalizer.normalize(base_request)
        assert result["time_bucket"] == "night"

    def test_dawn(self, normalizer, base_request):
        base_request.fishing_time = datetime(2026, 10, 1, 5, 30)
        result = normalizer.normalize(base_request)
        assert result["time_bucket"] == "dawn"

    def test_sunrise(self, normalizer, base_request):
        base_request.fishing_time = datetime(2026, 10, 1, 7, 0)
        result = normalizer.normalize(base_request)
        assert result["time_bucket"] == "sunrise"

    def test_sunset(self, normalizer, base_request):
        base_request.fishing_time = datetime(2026, 10, 1, 19, 0)
        result = normalizer.normalize(base_request)
        assert result["time_bucket"] == "sunset"


class TestSeaState:
    def test_flat(self, normalizer):
        assert normalizer._derive_sea_state(0.1) == "flat"

    def test_calm(self, normalizer):
        assert normalizer._derive_sea_state(0.3) == "calm"

    def test_light_chop(self, normalizer):
        assert normalizer._derive_sea_state(0.6) == "light_chop"

    def test_moderate(self, normalizer):
        assert normalizer._derive_sea_state(1.0) == "moderate"

    def test_working(self, normalizer):
        assert normalizer._derive_sea_state(1.3) == "working"

    def test_rough(self, normalizer):
        assert normalizer._derive_sea_state(2.0) == "rough"


class TestWindStrength:
    def test_calm(self, normalizer):
        assert normalizer._derive_wind_strength(5) == "calm"

    def test_light(self, normalizer):
        assert normalizer._derive_wind_strength(15) == "light"

    def test_moderate(self, normalizer):
        assert normalizer._derive_wind_strength(25) == "moderate"

    def test_strong(self, normalizer):
        assert normalizer._derive_wind_strength(40) == "strong"


class TestConditionMerging:
    def test_request_overrides_forecast(self, normalizer, base_request):
        base_request.conditions = Conditions(wave_height_m=1.0)
        forecast = {"marine": {"wave_height_m": 0.5}}
        
        result = normalizer.normalize(base_request, forecast)
        
        assert result["wave_height_m"] == 1.0  # Request value, not forecast

    def test_forecast_used_when_no_request(self, normalizer, base_request):
        forecast = {"marine": {"wave_height_m": 0.8}}
        
        result = normalizer.normalize(base_request, forecast)
        
        assert result["wave_height_m"] == 0.8


class TestObservations:
    def test_observations_included(self, normalizer, base_request):
        base_request.observations = Observations(
            foam=True,
            surface_activity=True,
            birds_diving=False,
        )
        
        result = normalizer.normalize(base_request)
        
        assert result["foam"] is True
        assert result["surface_activity"] is True
        assert result["birds_diving"] is False


class TestCompleteness:
    def test_minimal_completeness(self, normalizer):
        normalized = {
            "target_fish": "european_seabass",
            "rod_cast_max_g": 40,
        }
        score = normalizer.calculate_completeness(normalized)
        assert 0 < score < 1

    def test_full_completeness(self, normalizer):
        normalized = {
            "target_fish": "european_seabass",
            "rod_cast_max_g": 40,
            "time_bucket": "sunset",
            "sea_state": "moderate",
            "water_clarity": "clear",
            "structure": "reef",
            "wind_strength": "light",
            "foam": True,
            "surface_activity": False,
            "current_strength": "weak",
            "desired_layer": "shallow",
            "birds_diving": False,
        }
        score = normalizer.calculate_completeness(normalized)
        assert score == 1.0
