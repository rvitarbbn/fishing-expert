"""Equipment validator for checking lure-equipment compatibility."""

from typing import Any

from src.engine.candidate_generator import LureCandidate
from src.services.knowledge import KnowledgeBase


class EquipmentValidator:
    """Validates and selects equipment-compatible lure specifications."""

    def __init__(self, knowledge_base: KnowledgeBase):
        self.kb = knowledge_base

    def validate_and_select(
        self,
        candidates: list[LureCandidate],
        normalized: dict[str, Any],
    ) -> list[LureCandidate]:
        """
        Validate equipment compatibility and select specific weights.
        
        For each candidate:
        1. Check if any weight in range is compatible with rod
        2. Select optimal weight within compatible range
        3. Select appropriate length and color
        """
        rod_min = normalized.get("rod_cast_min_g", 0)
        rod_max = normalized.get("rod_cast_max_g", float("inf"))
        
        for candidate in candidates:
            if candidate.excluded:
                continue
            
            # Select weight
            self._select_weight(candidate, rod_min, rod_max, normalized)
            
            # Select length
            self._select_length(candidate, normalized)
            
            # Select color
            self._select_color(candidate, normalized)

        return candidates

    def _select_weight(
        self,
        candidate: LureCandidate,
        rod_min: float,
        rod_max: float,
        normalized: dict[str, Any],
    ) -> None:
        """Select optimal weight within rod range.

        If no weight in the lure's range overlaps the rod's range the
        candidate is hard-excluded here — this acts as a safety net for
        cases the rule evaluator did not catch (e.g. rules data missing
        the weight-exclusion entry for a particular lure type).
        """
        lure_min, lure_max = candidate.weight_range
        
        # Find overlap between lure range and rod range
        compatible_min = max(lure_min, rod_min)
        compatible_max = min(lure_max, rod_max)
        
        if compatible_min > compatible_max:
            # Hard-exclude: no usable weight exists for this rod
            candidate.exclude(
                "EQUIP_NO_WEIGHT_OVERLAP",
                "אין משקל מתאים לחכה — טווח הדמוי לא חופף לטווח ההטלה",
            )
            candidate.selected_weight_g = None
            return
        
        # Select weight based on conditions
        wind_strength = normalized.get("wind_strength")
        current_strength = normalized.get("current_strength")
        activity_distance = normalized.get("activity_distance")
        
        # Default to middle of compatible range
        optimal = (compatible_min + compatible_max) / 2
        
        # Adjust for conditions
        if wind_strength == "strong" or current_strength == "strong":
            # Prefer heavier for better control
            optimal = compatible_min + (compatible_max - compatible_min) * 0.75
        elif activity_distance == "far":
            # Prefer heavier for casting distance
            optimal = compatible_min + (compatible_max - compatible_min) * 0.8
        elif normalized.get("sea_state") in ("flat", "calm"):
            # Prefer lighter for finesse
            optimal = compatible_min + (compatible_max - compatible_min) * 0.4
        
        # Round to practical weight
        candidate.selected_weight_g = round(optimal)

    def _select_length(
        self,
        candidate: LureCandidate,
        normalized: dict[str, Any],
    ) -> None:
        """Select appropriate length based on conditions."""
        lure_min, lure_max = candidate.length_range
        
        target_fish = normalized.get("target_fish")
        
        # Default to middle of range
        optimal = (lure_min + lure_max) / 2
        
        # Adjust for target fish
        if target_fish in ("atlantic_bonito", "little_tunny", "greater_amberjack"):
            # Larger fish prefer larger lures
            optimal = lure_min + (lure_max - lure_min) * 0.7
        elif target_fish in ("european_seabass", "meagre"):
            # Medium size
            optimal = lure_min + (lure_max - lure_min) * 0.5
        elif target_fish == "unknown":
            # Conservative middle ground
            optimal = lure_min + (lure_max - lure_min) * 0.5
        
        candidate.selected_length_cm = round(optimal, 1)

    def _select_color(
        self,
        candidate: LureCandidate,
        normalized: dict[str, Any],
    ) -> None:
        """Select appropriate color family based on conditions."""
        water_clarity = normalized.get("water_clarity")
        time_bucket = normalized.get("time_bucket")
        foam = normalized.get("foam")
        
        # Get all color families
        colors = self.kb.get_all_colors()
        
        # Score each color
        best_color = "natural_sardine"  # Default
        best_score = 0
        
        for color_id, color_data in colors.items():
            score = 0
            best_for = color_data.get("best_for", [])
            
            if water_clarity and water_clarity in best_for:
                score += 10
            if time_bucket and time_bucket in best_for:
                score += 8
            if foam and "foam" in best_for:
                score += 5
            if "daylight" in best_for and time_bucket in ("morning", "midday", "afternoon"):
                score += 3
            if "low_light" in best_for and time_bucket in ("dawn", "dusk", "night"):
                score += 3
            
            if score > best_score:
                best_score = score
                best_color = color_id

        candidate.selected_color = best_color

    def get_compatibility_report(
        self,
        candidate: LureCandidate,
        normalized: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate equipment compatibility report for a candidate."""
        rod_min = normalized.get("rod_cast_min_g", 0)
        rod_max = normalized.get("rod_cast_max_g", float("inf"))
        lure_min, lure_max = candidate.weight_range
        
        weight_compatible = (
            candidate.selected_weight_g is not None
            and rod_min <= candidate.selected_weight_g <= rod_max
        )
        
        report = {
            "weight_within_range": weight_compatible,
            "rod_range_g": [rod_min, rod_max],
            "lure_range_g": [lure_min, lure_max],
            "selected_weight_g": candidate.selected_weight_g,
        }
        
        # Add warnings
        warnings = []
        if not weight_compatible:
            warnings.append("Selected weight may not be optimal for rod range")
        
        if candidate.selected_weight_g:
            if candidate.selected_weight_g > rod_max * 0.9:
                warnings.append("Weight is near rod maximum - cast carefully")
            if candidate.selected_weight_g < rod_min * 1.2:
                warnings.append("Weight is near rod minimum - may affect casting distance")
        
        report["warnings"] = warnings
        
        return report
