"""Tests for the rule evaluator."""

import pytest

from src.engine.candidate_generator import LureCandidate
from src.engine.rule_evaluator import RuleEvaluator
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
        "metal_jig": {
            "id": "metal_jig",
            "name_he": "ג׳יג מתכתי",
            "weight_g": [10, 120],
            "length_cm": [4, 16],
            "layers": ["surface", "midwater", "bottom"],
            "retrieves": ["fast_steady", "lift_fall"],
        },
    }
    kb.rules = [
        {
            "id": "BASE_seabass_minnow",
            "enabled": True,
            "priority": 50,
            "when": {"target_fish": "european_seabass"},
            "candidate": "minnow",
            "effect": {"score_delta": 25, "exclude": False},
            "reason_he": "מינו מתאים ללברק",
        },
        {
            "id": "COND_foam_minnow",
            "enabled": True,
            "priority": 40,
            "when": {"foam": True},
            "candidate": "minnow",
            "effect": {"score_delta": 18, "exclude": False},
            "reason_he": "קצף משפר הסוואה",
        },
        {
            "id": "HARD_WEIGHT_minnow",
            "enabled": True,
            "priority": 100,
            "when": {"candidate_weight_above_rod_max": True},
            "candidate": "minnow",
            "effect": {"score_delta": 0, "exclude": True},
            "reason_he": "משקל חורג מהחכה",
        },
    ]
    return kb


@pytest.fixture
def evaluator(knowledge_base):
    return RuleEvaluator(knowledge_base)


class TestSoftRules:
    def test_base_rule_applies_score(self, evaluator, knowledge_base):
        candidates = [
            LureCandidate("minnow", knowledge_base.lures["minnow"], base_score=50),
        ]
        normalized = {"target_fish": "european_seabass"}
        
        result = evaluator.evaluate_all(candidates, normalized)
        
        assert result[0].score == 75  # 50 + 25

    def test_condition_rule_stacks(self, evaluator, knowledge_base):
        candidates = [
            LureCandidate("minnow", knowledge_base.lures["minnow"], base_score=50),
        ]
        normalized = {"target_fish": "european_seabass", "foam": True}
        
        result = evaluator.evaluate_all(candidates, normalized)
        
        assert result[0].score == 93  # 50 + 25 + 18

    def test_contributing_rules_tracked(self, evaluator, knowledge_base):
        candidates = [
            LureCandidate("minnow", knowledge_base.lures["minnow"], base_score=50),
        ]
        normalized = {"target_fish": "european_seabass", "foam": True}
        
        result = evaluator.evaluate_all(candidates, normalized)
        
        assert "BASE_seabass_minnow" in result[0].contributing_rules
        assert "COND_foam_minnow" in result[0].contributing_rules


class TestHardExclusions:
    def test_weight_above_max_excludes(self, evaluator, knowledge_base):
        # Minnow min weight is 7g, rod max is 5g
        candidates = [
            LureCandidate("minnow", knowledge_base.lures["minnow"], base_score=50),
        ]
        normalized = {"rod_cast_max_g": 5}
        
        result = evaluator.evaluate_all(candidates, normalized)
        
        assert result[0].excluded is True

    def test_weight_within_range_not_excluded(self, evaluator, knowledge_base):
        candidates = [
            LureCandidate("minnow", knowledge_base.lures["minnow"], base_score=50),
        ]
        normalized = {"rod_cast_max_g": 40}
        
        result = evaluator.evaluate_all(candidates, normalized)
        
        assert result[0].excluded is False


class TestRanking:
    def test_ranking_by_score(self, evaluator, knowledge_base):
        candidates = [
            LureCandidate("minnow", knowledge_base.lures["minnow"], base_score=50),
            LureCandidate("metal_jig", knowledge_base.lures["metal_jig"], base_score=70),
        ]
        
        ranked = evaluator.rank_candidates(candidates, max_results=2)
        
        assert ranked[0].lure_id == "metal_jig"
        assert ranked[1].lure_id == "minnow"

    def test_excluded_filtered_out(self, evaluator, knowledge_base):
        candidates = [
            LureCandidate("minnow", knowledge_base.lures["minnow"], base_score=50),
            LureCandidate("metal_jig", knowledge_base.lures["metal_jig"], base_score=70),
        ]
        candidates[1].exclude("TEST", "test exclusion")
        
        ranked = evaluator.rank_candidates(candidates, max_results=2)
        
        assert len(ranked) == 1
        assert ranked[0].lure_id == "minnow"

    def test_score_capped_at_100(self, evaluator, knowledge_base):
        candidates = [
            LureCandidate("minnow", knowledge_base.lures["minnow"], base_score=90),
        ]
        candidates[0].score = 150  # Artificially high
        
        ranked = evaluator.rank_candidates(candidates)
        
        assert ranked[0].score == 100

    def test_score_capped_at_0(self, evaluator, knowledge_base):
        candidates = [
            LureCandidate("minnow", knowledge_base.lures["minnow"], base_score=10),
        ]
        candidates[0].score = -20  # Artificially low
        
        ranked = evaluator.rank_candidates(candidates)
        
        assert ranked[0].score == 0
