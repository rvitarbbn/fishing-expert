"""Tests for the equipment validator."""

import pytest

from src.engine.candidate_generator import LureCandidate
from src.engine.equipment_validator import EquipmentValidator
from src.services.knowledge import KnowledgeBase


@pytest.fixture
def knowledge_base():
    kb = KnowledgeBase()
    kb.lures = {
        "minnow": {
            "id": "minnow",
            "name_he": "מינו",
            "weight_g": [7, 40],
            "length_cm": [7, 16],
            "layers": ["surface", "shallow", "midwater"],
            "retrieves": ["steady", "slow_pause"],
        },
    }
    kb.colors = {
        "natural_sardine": {"id": "natural_sardine", "name_he": "סרדין טבעי", "best_for": ["clear", "bright"]},
        "chartreuse": {"id": "chartreuse", "name_he": "צהוב־ירקרק", "best_for": ["murky", "overcast"]},
    }
    return kb


@pytest.fixture
def validator(knowledge_base):
    return EquipmentValidator(knowledge_base)


class TestWeightSelection:
    def test_weight_within_rod_range(self, validator, knowledge_base):
        candidate = LureCandidate("minnow", knowledge_base.lures["minnow"])
        normalized = {"rod_cast_min_g": 10, "rod_cast_max_g": 40}
        
        validator._select_weight(candidate, 10, 40, normalized)
        
        assert candidate.selected_weight_g is not None
        assert 10 <= candidate.selected_weight_g <= 40

    def test_weight_heavier_in_strong_wind(self, validator, knowledge_base):
        candidate1 = LureCandidate("minnow", knowledge_base.lures["minnow"])
        candidate2 = LureCandidate("minnow", knowledge_base.lures["minnow"])
        
        validator._select_weight(candidate1, 10, 40, {"wind_strength": "calm"})
        validator._select_weight(candidate2, 10, 40, {"wind_strength": "strong"})
        
        assert candidate2.selected_weight_g > candidate1.selected_weight_g

    def test_weight_heavier_for_far_activity(self, validator, knowledge_base):
        candidate1 = LureCandidate("minnow", knowledge_base.lures["minnow"])
        candidate2 = LureCandidate("minnow", knowledge_base.lures["minnow"])
        
        validator._select_weight(candidate1, 10, 40, {"activity_distance": "near"})
        validator._select_weight(candidate2, 10, 40, {"activity_distance": "far"})
        
        assert candidate2.selected_weight_g > candidate1.selected_weight_g


class TestColorSelection:
    def test_clear_water_natural_color(self, validator, knowledge_base):
        candidate = LureCandidate("minnow", knowledge_base.lures["minnow"])
        normalized = {"water_clarity": "clear"}
        
        validator._select_color(candidate, normalized)
        
        assert candidate.selected_color == "natural_sardine"

    def test_murky_water_bright_color(self, validator, knowledge_base):
        candidate = LureCandidate("minnow", knowledge_base.lures["minnow"])
        normalized = {"water_clarity": "murky"}
        
        validator._select_color(candidate, normalized)
        
        assert candidate.selected_color == "chartreuse"


class TestCompatibilityReport:
    def test_compatible_weight_report(self, validator, knowledge_base):
        candidate = LureCandidate("minnow", knowledge_base.lures["minnow"])
        candidate.selected_weight_g = 25
        normalized = {"rod_cast_min_g": 10, "rod_cast_max_g": 40}
        
        report = validator.get_compatibility_report(candidate, normalized)
        
        assert report["weight_within_range"] is True
        assert report["selected_weight_g"] == 25

    def test_incompatible_weight_report(self, validator, knowledge_base):
        candidate = LureCandidate("minnow", knowledge_base.lures["minnow"])
        candidate.selected_weight_g = 50  # Above rod max
        normalized = {"rod_cast_min_g": 10, "rod_cast_max_g": 40}
        
        report = validator.get_compatibility_report(candidate, normalized)
        
        assert report["weight_within_range"] is False

    def test_near_max_warning(self, validator, knowledge_base):
        candidate = LureCandidate("minnow", knowledge_base.lures["minnow"])
        candidate.selected_weight_g = 38  # 95% of max
        normalized = {"rod_cast_min_g": 10, "rod_cast_max_g": 40}
        
        report = validator.get_compatibility_report(candidate, normalized)
        
        assert any("near rod maximum" in w for w in report["warnings"])
