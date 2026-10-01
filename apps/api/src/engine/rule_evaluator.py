"""Rule evaluator for applying soft and hard rules to candidates."""

from typing import Any

from src.engine.candidate_generator import LureCandidate
from src.services.knowledge import KnowledgeBase


class RuleEvaluator:
    """Evaluates rules against candidates and normalized conditions."""

    def __init__(self, knowledge_base: KnowledgeBase):
        self.kb = knowledge_base

    def evaluate_all(
        self,
        candidates: list[LureCandidate],
        normalized: dict[str, Any],
    ) -> list[LureCandidate]:
        """
        Apply all enabled rules to candidates.
        
        Rules are applied in priority order (higher priority first).
        Hard exclusion rules are applied after soft scoring rules.
        """
        rules = self.kb.get_all_rules()
        
        # Sort rules by priority (higher first)
        sorted_rules = sorted(
            rules,
            key=lambda r: r.get("priority", 50),
            reverse=True,
        )

        # First pass: apply soft rules (score deltas)
        for rule in sorted_rules:
            if not rule.get("enabled", True):
                continue
            
            effect = rule.get("effect", {})
            if effect.get("exclude", False):
                continue  # Skip hard rules in first pass
            
            self._apply_rule(rule, candidates, normalized)

        # Second pass: apply hard exclusion rules
        for rule in sorted_rules:
            if not rule.get("enabled", True):
                continue
            
            effect = rule.get("effect", {})
            if not effect.get("exclude", False):
                continue  # Skip soft rules in second pass
            
            self._apply_rule(rule, candidates, normalized)

        return candidates

    def _apply_rule(
        self,
        rule: dict[str, Any],
        candidates: list[LureCandidate],
        normalized: dict[str, Any],
    ) -> None:
        """Apply a single rule to matching candidates."""
        rule_id = rule.get("id", "unknown")
        when = rule.get("when", {})
        candidate_type = rule.get("candidate")
        effect = rule.get("effect", {})
        reason_he = rule.get("reason_he", "")

        # Check if rule conditions match normalized input
        if not self._conditions_match(when, normalized):
            return

        # Apply to matching candidates
        for candidate in candidates:
            if candidate.excluded:
                continue  # Skip already excluded candidates
            
            # Check if rule applies to this candidate type
            if candidate_type and candidate.lure_id != candidate_type:
                continue

            # Check special weight conditions
            if "candidate_weight_above_rod_max" in when:
                if not self._check_weight_above_max(candidate, normalized):
                    continue
            
            if "candidate_weight_below_rod_min_materially" in when:
                if not self._check_weight_below_min(candidate, normalized):
                    continue

            # Apply effect
            if effect.get("exclude", False):
                candidate.exclude(rule_id, reason_he)
            else:
                score_delta = effect.get("score_delta", 0)
                candidate.apply_rule(rule_id, score_delta, reason_he)

    def _conditions_match(
        self,
        when: dict[str, Any],
        normalized: dict[str, Any],
    ) -> bool:
        """Check if all rule conditions match the normalized input."""
        for key, expected in when.items():
            # Skip special weight conditions (handled separately)
            if key in ("candidate_weight_above_rod_max", "candidate_weight_below_rod_min_materially"):
                continue
            
            actual = normalized.get(key)
            
            # Handle boolean conditions
            if isinstance(expected, bool):
                if actual != expected:
                    return False
            # Handle string/value conditions
            elif actual != expected:
                return False

        return True

    def _check_weight_above_max(
        self,
        candidate: LureCandidate,
        normalized: dict[str, Any],
    ) -> bool:
        """Check if candidate's minimum weight exceeds rod maximum."""
        rod_max = normalized.get("rod_cast_max_g")
        if rod_max is None:
            return False
        
        min_weight = candidate.weight_range[0]
        return min_weight > rod_max

    def _check_weight_below_min(
        self,
        candidate: LureCandidate,
        normalized: dict[str, Any],
    ) -> bool:
        """Check if candidate's maximum weight is materially below rod minimum."""
        rod_min = normalized.get("rod_cast_min_g")
        if rod_min is None:
            return False
        
        max_weight = candidate.weight_range[1]
        # "Materially below" means max weight is less than 70% of rod minimum
        return max_weight < rod_min * 0.7

    def rank_candidates(
        self,
        candidates: list[LureCandidate],
        max_results: int = 3,
    ) -> list[LureCandidate]:
        """
        Rank candidates by score and return top results.
        
        Excluded candidates are filtered out.
        Scores are capped to 0-100 range.
        """
        # Filter out excluded candidates
        valid_candidates = [c for c in candidates if not c.excluded]
        
        # Cap scores to 0-100
        for candidate in valid_candidates:
            candidate.score = max(0, min(100, candidate.score))
        
        # Sort by score descending
        ranked = sorted(valid_candidates, key=lambda c: c.score, reverse=True)
        
        return ranked[:max_results]
