"""
Tests for the 60 seed scenarios from the specification.

These tests verify that the recommendation engine produces correct
results for all documented test cases.

IMPORTANT: ``test_scenarios.json`` is checked into the repo alongside
this file.  If missing, tests FAIL — they never silently skip.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from src.engine.recommendation_engine import RecommendationEngine
from src.schemas.recommendation import (
    Conditions,
    Equipment,
    Location,
    Observations,
    RecommendationRequest,
)
from src.services.knowledge import KnowledgeBase

# ── Fixed, deterministic paths ──────────────────────────────────────────
_TESTS_DIR = Path(__file__).parent
_SCENARIOS_FILE = _TESTS_DIR / "test_scenarios.json"

_KNOWLEDGE_PATHS = [
    Path(__file__).parent.parent.parent.parent / "packages" / "knowledge",
    Path("/app/packages/knowledge"),
    Path("packages/knowledge"),
]


@pytest.fixture
def knowledge_base():
    """Load the actual knowledge base from seed files.

    FAILS (not skips) when the knowledge directory cannot be found.
    """
    kb = KnowledgeBase()
    for path in _KNOWLEDGE_PATHS:
        if path.exists():
            kb.load_from_directory(path)
            return kb
    pytest.fail(
        "Knowledge directory not found in any of: "
        + ", ".join(str(p) for p in _KNOWLEDGE_PATHS)
    )


@pytest.fixture
def engine(knowledge_base):
    return RecommendationEngine(knowledge_base)


@pytest.fixture
def test_scenarios():
    """Load test scenarios — FAILS if the file is absent."""
    if not _SCENARIOS_FILE.exists():
        pytest.fail(
            f"test_scenarios.json not found at {_SCENARIOS_FILE}. "
            "This file must be checked into the repository."
        )
    return json.loads(_SCENARIOS_FILE.read_text(encoding="utf-8"))["scenarios"]


def build_request_from_scenario(scenario: dict[str, Any]) -> RecommendationRequest:
    """Build a RecommendationRequest from a test scenario."""
    input_data = scenario["input"]
    rod = input_data.get("rod", [10, 40])
    
    return RecommendationRequest(
        target_fish=input_data.get("target_fish", "unknown"),
        fishing_time="2026-10-01T18:00:00",
        location=Location(
            name="Test Location",
            structure=input_data.get("structure"),
        ),
        conditions=Conditions(
            water_clarity=input_data.get("water_clarity"),
            sea_state=input_data.get("sea_state"),
            current_strength=input_data.get("current_strength"),
            desired_layer=input_data.get("desired_layer"),
        ),
        observations=Observations(
            foam=input_data.get("foam"),
            surface_activity=input_data.get("surface_activity"),
            birds_diving=input_data.get("birds_diving"),
            activity_distance=input_data.get("activity_distance"),
        ),
        equipment=Equipment(
            rod_cast_min_g=rod[0],
            rod_cast_max_g=rod[1],
        ),
    )


class TestSeedScenarios:
    """Test all 60 seed scenarios."""

    def test_scenario_count(self, test_scenarios):
        """Verify we have all 60 scenarios."""
        assert len(test_scenarios) == 60

    @pytest.mark.parametrize("scenario_id", [f"T{i:03d}" for i in range(1, 61)])
    def test_scenario(self, scenario_id, test_scenarios, engine):
        """Test individual scenario."""
        scenario = next((s for s in test_scenarios if s["id"] == scenario_id), None)
        if not scenario:
            pytest.fail(f"Scenario {scenario_id} not found in test_scenarios.json")
        
        request = build_request_from_scenario(scenario)
        response = engine.recommend(request)
        
        # Check invariants
        invariants = scenario.get("invariants", [])
        
        if "deterministic" in invariants:
            # Run again and compare full deterministic payload
            response2 = engine.recommend(request)
            # recommendation_id is deterministic — must be identical
            assert response.recommendation_id == response2.recommendation_id
            assert response.primary.lure_type == response2.primary.lure_type
            assert response.primary.suitability_score == response2.primary.suitability_score
            assert response.primary.recommended_weight_g == response2.primary.recommended_weight_g
            assert response.primary.color_family == response2.primary.color_family
            assert response.primary.retrieve_method == response2.primary.retrieve_method
            assert response.primary.contributing_rule_ids == response2.primary.contributing_rule_ids
            assert response.rules_version == response2.rules_version
            # Alternatives must match in count and content
            assert len(response.alternatives) == len(response2.alternatives)
            for a1, a2 in zip(response.alternatives, response2.alternatives):
                assert a1.recommendation.lure_type == a2.recommendation.lure_type
                assert a1.recommendation.suitability_score == a2.recommendation.suitability_score
        
        if "three_or_fewer_recommendations" in invariants:
            assert len(response.alternatives) <= 2
        
        if "reasons_present" in invariants:
            assert len(response.reasons) > 0
        
        if "rules_version_present" in invariants:
            assert response.rules_version is not None
        
        # Check weight constraint
        must_not_exceed = scenario.get("must_not_exceed_g")
        if must_not_exceed:
            assert response.primary.recommended_weight_g <= must_not_exceed, \
                f"Weight {response.primary.recommended_weight_g}g exceeds max {must_not_exceed}g"
        
        # Check expected top lure
        expect_top = scenario.get("expect_top_any", [])
        if expect_top:
            assert response.primary.lure_type in expect_top, \
                f"Expected one of {expect_top}, got {response.primary.lure_type}"
        
        # Check excluded lures
        expect_not_top = scenario.get("expect_not_top", [])
        if expect_not_top:
            assert response.primary.lure_type not in expect_not_top, \
                f"Did not expect {response.primary.lure_type} as top recommendation"


class TestDeterminism:
    """Test that the engine is deterministic."""

    def test_same_input_same_output(self, engine):
        """Same normalized request returns identical result (full payload)."""
        request = RecommendationRequest(
            target_fish="european_seabass",
            fishing_time="2026-10-01T18:00:00",
            location=Location(name="Test", structure="mixed"),
            conditions=Conditions(water_clarity="clear", sea_state="moderate"),
            observations=Observations(foam=True),
            equipment=Equipment(rod_cast_min_g=10, rod_cast_max_g=40),
        )
        
        result1 = engine.recommend(request)
        result2 = engine.recommend(request)

        # Deterministic fingerprint must be identical
        assert result1.recommendation_id == result2.recommendation_id

        # Full primary recommendation must match
        assert result1.primary.lure_type == result2.primary.lure_type
        assert result1.primary.suitability_score == result2.primary.suitability_score
        assert result1.primary.recommended_weight_g == result2.primary.recommended_weight_g
        assert result1.primary.color_family == result2.primary.color_family
        assert result1.primary.contributing_rule_ids == result2.primary.contributing_rule_ids

        # Alternatives must match
        assert len(result1.alternatives) == len(result2.alternatives)


class TestWeightConstraints:
    """Test that weight constraints are enforced."""

    def test_no_weight_above_rod_max(self, engine):
        """No returned weight exceeds rod maximum."""
        request = RecommendationRequest(
            target_fish="european_seabass",
            fishing_time="2026-10-01T18:00:00",
            location=Location(name="Test"),
            equipment=Equipment(rod_cast_min_g=5, rod_cast_max_g=25),
        )
        
        result = engine.recommend(request)
        
        assert result.primary.recommended_weight_g <= 25
        for alt in result.alternatives:
            assert alt.recommendation.recommended_weight_g <= 25


class TestRuleContribution:
    """Test that rule IDs are properly tracked."""

    def test_contributing_rules_present(self, engine):
        """Every ranked candidate includes contributing rule IDs."""
        request = RecommendationRequest(
            target_fish="bluefish",
            fishing_time="2026-10-01T07:00:00",
            location=Location(name="Test"),
            observations=Observations(surface_activity=True),
            equipment=Equipment(rod_cast_min_g=20, rod_cast_max_g=60),
        )
        
        result = engine.recommend(request)
        
        assert len(result.primary.contributing_rule_ids) > 0
        for alt in result.alternatives:
            assert len(alt.recommendation.contributing_rule_ids) > 0
