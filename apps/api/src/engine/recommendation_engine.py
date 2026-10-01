"""Main recommendation engine orchestrating all components."""

import hashlib
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from src.engine.candidate_generator import CandidateGenerator, LureCandidate
from src.engine.equipment_validator import EquipmentValidator
from src.engine.normalizer import Normalizer
from src.engine.rule_evaluator import RuleEvaluator
from src.schemas.recommendation import (
    AlternativeRecommendation,
    DataQuality,
    LureRecommendation,
    RecommendationRequest,
    RecommendationResponse,
)
from src.services.knowledge import KnowledgeBase

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Deterministic recommendation engine.
    
    Pipeline:
    1. Validate and normalize request
    2. Enrich with forecast if allowed
    3. Derive categorical conditions
    4. Generate lure candidates from catalog
    5. Apply fish base preferences
    6. Apply soft rules as score deltas
    7. Apply hard exclusions
    8. Select compatible size/weight/color/retrieve
    9. Rank, normalize to 0-100 suitability and return top three
    10. Produce reasons and counterfactual switch conditions
    """

    def __init__(self, knowledge_base: KnowledgeBase):
        self.kb = knowledge_base
        self.normalizer = Normalizer(known_fish_ids=set(knowledge_base.get_all_fish().keys()))
        self.candidate_generator = CandidateGenerator(knowledge_base)
        self.rule_evaluator = RuleEvaluator(knowledge_base)
        self.equipment_validator = EquipmentValidator(knowledge_base)

    def recommend(
        self,
        request: RecommendationRequest,
        forecast: Optional[dict[str, Any]] = None,
    ) -> RecommendationResponse:
        """
        Generate deterministic lure recommendations.
        
        Same normalized request and rules version returns identical results.
        """
        logger.info(f"Processing recommendation for {request.target_fish}")
        
        # Step 1-3: Normalize inputs
        normalized = self.normalizer.normalize(request, forecast)
        logger.debug(f"Normalized conditions: {normalized}")
        
        # Step 4: Generate candidates
        candidates = self.candidate_generator.generate_candidates(
            normalized,
            base_score=self.kb.get_scoring_start(),
        )
        logger.debug(f"Generated {len(candidates)} candidates")
        
        # Step 5-7: Apply rules (soft scoring and hard exclusions)
        candidates = self.rule_evaluator.evaluate_all(candidates, normalized)
        
        # Step 8: Validate equipment and select specifications
        candidates = self.equipment_validator.validate_and_select(candidates, normalized)
        
        # Step 9: Rank and get top 3
        ranked = self.rule_evaluator.rank_candidates(candidates, max_results=3)
        
        if not ranked:
            # No valid candidates - return error response
            raise ValueError("No compatible lures found for the given conditions and equipment")
        
        # Step 10: Build response
        response = self._build_response(
            request=request,
            ranked=ranked,
            normalized=normalized,
            forecast=forecast,
        )
        
        logger.info(f"Recommendation complete: {response.recommendation_id}")
        return response

    def _build_response(
        self,
        request: RecommendationRequest,
        ranked: list[LureCandidate],
        normalized: dict[str, Any],
        forecast: Optional[dict[str, Any]],
    ) -> RecommendationResponse:
        """Build the recommendation response from ranked candidates."""
        # Generate deterministic recommendation ID
        rec_id = self._generate_recommendation_id(normalized)
        
        # Build primary recommendation
        primary = self._build_lure_recommendation(ranked[0])
        
        # Build alternatives with switch conditions
        alternatives = []
        for i, candidate in enumerate(ranked[1:3], start=1):
            alt = AlternativeRecommendation(
                recommendation=self._build_lure_recommendation(candidate),
                switch_condition_he=self._generate_switch_condition(ranked[0], candidate, i),
            )
            alternatives.append(alt)
        
        # Collect all reasons from primary
        reasons = ranked[0].reasons_he.copy()
        
        # Generate warnings
        warnings = self._generate_warnings(normalized, request)
        
        # Identify missing information
        missing = self._identify_missing_info(normalized)
        
        # Equipment compatibility
        equipment_compat = self.equipment_validator.get_compatibility_report(
            ranked[0], normalized
        )
        
        # Data quality
        completeness = self.normalizer.calculate_completeness(normalized)
        data_quality = DataQuality(
            completeness_score=completeness,
            forecast_confidence=forecast.get("confidence") if forecast else None,
            forecast_timestamp=datetime.fromisoformat(forecast["fetch_timestamp"]) if forecast and "fetch_timestamp" in forecast else None,
            forecast_provider=forecast.get("provider") if forecast else None,
            data_source="forecast" if forecast else "user_supplied",
        )
        
        return RecommendationResponse(
            recommendation_id=rec_id,
            request_timestamp=datetime.utcnow(),
            primary=primary,
            alternatives=alternatives,
            normalized_conditions=normalized,
            reasons=reasons,
            warnings=warnings,
            missing_information=missing,
            equipment_compatibility=equipment_compat,
            data_quality=data_quality,
            rules_version=self.kb.rules_version,
            knowledge_version=self.kb.knowledge_version,
        )

    def _build_lure_recommendation(
        self,
        candidate: LureCandidate,
    ) -> LureRecommendation:
        """Build a LureRecommendation from a candidate.

        Only ranked (non-excluded) candidates should reach this point,
        so ``selected_weight_g`` must already be set.  If it is somehow
        ``None`` we clamp to the lure's minimum weight and add a warning
        so the gap is visible rather than silently hidden.
        """
        lure_data = candidate.lure_data
        retrieve_data = self.kb.get_retrieve(candidate.selected_retrieve) or {}
        color_data = self.kb.get_color(candidate.selected_color) or {}

        # Defensive: if weight selection was skipped, clamp to rod max
        weight = candidate.selected_weight_g
        if weight is None:
            logger.warning(
                "Candidate %s reached build without selected_weight_g — "
                "this should not happen after equipment validation",
                candidate.lure_id,
            )
            rod_max = candidate.lure_data.get("weight_g", [0, 0])[1]
            weight = rod_max  # will be capped by schema ge constraint

        return LureRecommendation(
            lure_type=candidate.lure_id,
            lure_name_he=lure_data.get("name_he", candidate.lure_id),
            length_cm_range=candidate.length_range,
            weight_g_range=candidate.weight_range,
            recommended_weight_g=weight,
            color_family=candidate.selected_color or "natural_sardine",
            working_layer=getattr(candidate, "selected_layer", candidate.layers[0] if candidate.layers else "midwater"),
            retrieve_method=candidate.selected_retrieve or "steady",
            retrieve_steps_he=retrieve_data.get("steps_he", []),
            suitability_score=candidate.score,
            contributing_rule_ids=candidate.contributing_rules,
        )

    def _generate_switch_condition(
        self,
        primary: LureCandidate,
        alternative: LureCandidate,
        position: int,
    ) -> str:
        """Generate Hebrew switch condition for an alternative."""
        # Analyze differences between primary and alternative
        alt_layers = set(alternative.layers)
        primary_layers = set(primary.layers)
        
        if "surface" in alt_layers and "surface" not in primary_layers:
            return "עבור לדמוי זה אם תראה פעילות בפני המים"
        elif "bottom" in alt_layers and "bottom" not in primary_layers:
            return "עבור לדמוי זה אם הדגים לא מגיבים בשכבה העליונה"
        elif alternative.lure_id == "metal_jig":
            return "עבור לג׳יג אם הפעילות רחוקה או הרוח מתחזקת"
        elif alternative.lure_id == "soft_plastic":
            return "עבור לסיליקון אם הדגים זהירים או המים עכורים"
        elif alternative.lure_id in ("popper", "pencil"):
            return "עבור לטופ־ווטר אם תראה רדיפות בפני המים"
        else:
            return f"נסה חלופה {position} אם אין תגובה לדמוי הראשי"

    def _generate_warnings(
        self,
        normalized: dict[str, Any],
        request: RecommendationRequest,
    ) -> list[str]:
        """Generate safety and legal warnings."""
        warnings = []
        
        # Sea state warnings
        sea_state = normalized.get("sea_state")
        if sea_state in ("rough", "working"):
            warnings.append(
                "הנתונים מצביעים על תנאים שעלולים להיות מסוכנים. "
                "אין להסתמך על האפליקציה להחלטת בטיחות. "
                "בדוק אזהרות רשמיות, הימנע מסלעים ושוברי גלים חשופים."
            )
        
        # Wind warnings
        wind_strength = normalized.get("wind_strength")
        if wind_strength == "strong":
            warnings.append(
                "רוח חזקה עלולה להשפיע על ההטלה ועל הבטיחות. "
                "שקול לדחות את הדיג או לבחור מיקום מוגן."
            )
        
        # Unknown fish warning
        if not normalized.get("target_fish_recognized", True):
            warnings.append(
                "דג המטרה שצוין לא מוכר במערכת. "
                "ההמלצות מבוססות על חוקים כלליים בלבד ועשויות להיות פחות מדויקות."
            )

        # Legal reminder
        warnings.append(
            "סטטוס חוקי, עונות איסור, שמורות ומינים מוגנים עשויים להשתנות. "
            "על המשתמש לבדוק את המקור הממשלתי העדכני לפני הדיג."
        )
        
        return warnings

    def _identify_missing_info(
        self,
        normalized: dict[str, Any],
    ) -> list[str]:
        """Identify missing information that could improve recommendations."""
        missing = []
        
        if normalized.get("water_clarity") is None:
            missing.append("צלילות המים - משפיעה על בחירת צבע ודמוי")
        
        if normalized.get("sea_state") is None and normalized.get("wave_height_m") is None:
            missing.append("מצב הים או גובה גלים - משפיע על בחירת משקל ודמוי")
        
        if normalized.get("structure") is None:
            missing.append("סוג המבנה (סלעי, חולי, שובר גלים) - משפיע על טכניקת העבודה")
        
        if normalized.get("surface_activity") is None:
            missing.append("פעילות בפני המים - משפיעה על בחירת דמויי טופ־ווטר")
        
        return missing

    def _generate_recommendation_id(
        self,
        normalized: dict[str, Any],
    ) -> str:
        """Generate a *deterministic* recommendation fingerprint.

        The ID is derived entirely from the normalised input and rules
        version so that identical inputs always produce the identical ID.
        Instance-level metadata (wall-clock time, audit row key) is kept
        separate by the caller.
        """
        payload = {
            "normalized": normalized,
            "rules_version": self.kb.rules_version,
            "knowledge_version": self.kb.knowledge_version,
        }
        content = json.dumps(payload, sort_keys=True, default=str)
        digest = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"rec_{digest}"
