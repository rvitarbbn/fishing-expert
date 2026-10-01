"""Candidate generator for lure recommendations."""

from typing import Any

from src.services.knowledge import KnowledgeBase


class LureCandidate:
    """A candidate lure for recommendation."""

    def __init__(
        self,
        lure_id: str,
        lure_data: dict[str, Any],
        base_score: int = 50,
    ):
        self.lure_id = lure_id
        self.lure_data = lure_data
        self.score = base_score
        self.contributing_rules: list[str] = []
        self.reasons_he: list[str] = []
        self.excluded = False
        self.exclusion_reason: str | None = None
        
        # Weight selection (will be refined by equipment validator)
        self.selected_weight_g: float | None = None
        self.selected_length_cm: float | None = None
        self.selected_color: str | None = None
        self.selected_retrieve: str | None = None

    @property
    def weight_range(self) -> tuple[float, float]:
        """Get weight range from lure data."""
        return tuple(self.lure_data.get("weight_g", [0, 0]))

    @property
    def length_range(self) -> tuple[float, float]:
        """Get length range from lure data."""
        return tuple(self.lure_data.get("length_cm", [0, 0]))

    @property
    def layers(self) -> list[str]:
        """Get compatible water layers."""
        return self.lure_data.get("layers", [])

    @property
    def retrieves(self) -> list[str]:
        """Get compatible retrieve methods."""
        return self.lure_data.get("retrieves", [])

    def apply_rule(self, rule_id: str, score_delta: int, reason_he: str) -> None:
        """Apply a soft rule to this candidate."""
        self.score += score_delta
        self.contributing_rules.append(rule_id)
        if reason_he and reason_he not in self.reasons_he:
            self.reasons_he.append(reason_he)

    def exclude(self, rule_id: str, reason_he: str) -> None:
        """Mark this candidate as excluded by a hard rule."""
        self.excluded = True
        self.exclusion_reason = reason_he
        self.contributing_rules.append(rule_id)

    def __repr__(self) -> str:
        status = "EXCLUDED" if self.excluded else f"score={self.score}"
        return f"LureCandidate({self.lure_id}, {status})"


class CandidateGenerator:
    """Generates lure candidates from the catalog based on target fish."""

    def __init__(self, knowledge_base: KnowledgeBase):
        self.kb = knowledge_base

    # Score bonus applied to lures that appear in the target fish's
    # ``preferred_lures`` list.  This ensures fish-preference data is
    # always reflected in the recommendation even if the seed rules
    # happen to be missing a BASE_ entry for the combination.
    FISH_PREFERENCE_BONUS: int = 15

    def generate_candidates(
        self,
        normalized: dict[str, Any],
        base_score: int = 50,
    ) -> list[LureCandidate]:
        """
        Generate candidate lures based on target fish and conditions.
        
        All lures start as candidates.  Lures that appear in the target
        fish's ``preferred_lures`` list receive a score bonus upfront.
        """
        target_fish = normalized.get("target_fish", "unknown")
        fish_data = self.kb.get_fish(target_fish)
        
        candidates: list[LureCandidate] = []
        
        # Get all lures from catalog
        all_lures = self.kb.get_all_lures()
        
        # Preferred-lure set for the target fish
        preferred_lures: set[str] = set()
        if fish_data:
            preferred_lures = set(fish_data.get("preferred_lures", []))

        for lure_id, lure_data in all_lures.items():
            candidate = LureCandidate(
                lure_id=lure_id,
                lure_data=lure_data,
                base_score=base_score,
            )

            # Apply fish-preference boost
            if lure_id in preferred_lures:
                candidate.apply_rule(
                    f"FISH_PREF_{target_fish}_{lure_id}",
                    self.FISH_PREFERENCE_BONUS,
                    fish_data.get("name_he", target_fish) + " — דמוי מועדף",
                )
            
            # Pre-select compatible retrieve and layer based on conditions
            self._preselect_retrieve(candidate, normalized)
            self._preselect_layer(candidate, normalized)
            
            candidates.append(candidate)

        # Add a warning when fish is unrecognized
        if not normalized.get("target_fish_recognized", True):
            for c in candidates:
                c.apply_rule(
                    "WARN_UNKNOWN_FISH",
                    0,
                    "דג מטרה לא מוכר — ההמלצות מבוססות על חוקים כלליים בלבד",
                )

        return candidates

    def _preselect_retrieve(
        self,
        candidate: LureCandidate,
        normalized: dict[str, Any],
    ) -> None:
        """Pre-select the most appropriate retrieve method."""
        retrieves = candidate.retrieves
        if not retrieves:
            return

        target_fish = normalized.get("target_fish")
        time_bucket = normalized.get("time_bucket")
        
        # Get retrieve data for scoring
        best_retrieve = retrieves[0]  # Default to first
        best_score = 0
        
        for retrieve_id in retrieves:
            retrieve_data = self.kb.get_retrieve(retrieve_id)
            if not retrieve_data:
                continue
            
            score = 0
            use_when = retrieve_data.get("use_when", [])
            
            # Score based on matching conditions
            if target_fish and target_fish in use_when:
                score += 10
            if time_bucket and time_bucket in use_when:
                score += 5
            if candidate.lure_id in use_when:
                score += 3
            
            if score > best_score:
                best_score = score
                best_retrieve = retrieve_id

        candidate.selected_retrieve = best_retrieve

    def _preselect_layer(
        self,
        candidate: LureCandidate,
        normalized: dict[str, Any],
    ) -> None:
        """Pre-select the most appropriate water layer."""
        layers = candidate.layers
        if not layers:
            return

        desired_layer = normalized.get("desired_layer")
        
        if desired_layer and desired_layer in layers:
            candidate.selected_layer = desired_layer
        else:
            # Default to first compatible layer
            candidate.selected_layer = layers[0]
