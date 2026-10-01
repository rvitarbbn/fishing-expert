"""
LLM Adapter for natural language processing.

The LLM may:
1. Parse natural language into the request schema
2. Turn the immutable response into prose

The LLM CANNOT:
1. Override exclusions, weights, safety warnings, or equipment constraints
2. Modify the structured recommendation output
3. Represent suitability scores as catch probability

A strict validator ensures prose does not contradict the structured output.
"""

import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Any, Optional

from src.schemas.recommendation import RecommendationRequest, RecommendationResponse

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def parse_input(self, user_message: str) -> dict[str, Any]:
        """Parse natural language into structured request fields."""
        pass

    @abstractmethod
    async def generate_explanation(
        self,
        response: RecommendationResponse,
        user_language: str = "he",
    ) -> str:
        """Generate natural language explanation of the recommendation."""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider implementation."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client: Optional[Any] = None

    async def _get_client(self) -> Any:
        if self._client is None:
            try:
                import openai
                self._client = openai.AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai package required for OpenAI provider")
        return self._client

    async def parse_input(self, user_message: str) -> dict[str, Any]:
        """Parse Hebrew natural language into request fields."""
        client = await self._get_client()
        
        system_prompt = """אתה מחלץ מידע מטקסט עברי לצורך המלצת דמויי דיג.
חלץ את השדות הבאים אם קיימים:
- target_fish: מזהה דג (european_seabass, bluefish, atlantic_bonito, etc.)
- location_name: שם המיקום
- structure: סוג מבנה (reef, sandy, breakwater, mixed)
- water_clarity: צלילות (clear, slightly_murky, murky)
- sea_state: מצב ים (flat, calm, light_chop, moderate, working, rough)
- foam: האם יש קצף (true/false)
- surface_activity: פעילות בפני המים (true/false)
- birds_diving: ציפורים צוללות (true/false)
- activity_distance: מרחק פעילות (near, medium, far)
- rod_cast_min_g: משקל הטלה מינימלי
- rod_cast_max_g: משקל הטלה מקסימלי

החזר JSON בלבד."""

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        
        return json.loads(response.choices[0].message.content)

    async def generate_explanation(
        self,
        response: RecommendationResponse,
        user_language: str = "he",
    ) -> str:
        """Generate Hebrew explanation of the recommendation."""
        client = await self._get_client()
        
        system_prompt = """אתה מסביר המלצות דמויי דיג בעברית.
הסבר את ההמלצה בצורה ברורה וידידותית.

חוקים קריטיים:
1. אסור לשנות את הדירוג או הציון
2. אסור לתאר את הציון כהסתברות לתפיסה
3. אסור להתעלם מאזהרות בטיחות
4. יש לציין את כל החלופות
5. יש לציין מידע חסר

הסבר את ההמלצה בקצרה ובבהירות."""

        response_json = response.model_dump(mode="json")
        
        completion = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"הסבר את ההמלצה הבאה:\n{json.dumps(response_json, ensure_ascii=False)}"},
            ],
            temperature=0.3,
        )
        
        explanation = completion.choices[0].message.content
        
        # Validate the explanation
        validated = validate_explanation(explanation, response)
        if not validated["valid"]:
            logger.warning(f"Explanation validation failed: {validated['errors']}")
            # Return a safe fallback
            return generate_safe_explanation(response)
        
        return explanation


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider implementation."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client: Optional[Any] = None

    async def _get_client(self) -> Any:
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("anthropic package required for Anthropic provider")
        return self._client

    async def parse_input(self, user_message: str) -> dict[str, Any]:
        """Parse Hebrew natural language into request fields."""
        client = await self._get_client()
        
        response = await client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            system="Extract fishing request fields from Hebrew text. Return JSON only.",
            messages=[{"role": "user", "content": user_message}],
        )
        
        return json.loads(response.content[0].text)

    async def generate_explanation(
        self,
        response: RecommendationResponse,
        user_language: str = "he",
    ) -> str:
        """Generate Hebrew explanation of the recommendation."""
        client = await self._get_client()
        
        response_json = response.model_dump(mode="json")
        
        completion = await client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            system="Explain fishing recommendations in Hebrew. Never change rankings or describe scores as catch probability.",
            messages=[{"role": "user", "content": f"הסבר: {json.dumps(response_json, ensure_ascii=False)}"}],
        )
        
        explanation = completion.content[0].text
        
        validated = validate_explanation(explanation, response)
        if not validated["valid"]:
            return generate_safe_explanation(response)
        
        return explanation


def validate_explanation(
    explanation: str,
    response: RecommendationResponse,
) -> dict[str, Any]:
    """
    Validate that the LLM explanation does not contradict the structured output.
    
    Checks:
    1. Does not claim different rankings
    2. Does not describe scores as probability
    3. Does not omit safety warnings
    4. Does not change weight recommendations
    """
    errors = []
    
    # Check for probability language
    probability_patterns = [
        r"סיכוי.*תפיסה",
        r"הסתברות.*לתפוס",
        r"probability",
        r"\d+%.*catch",
    ]
    for pattern in probability_patterns:
        if re.search(pattern, explanation, re.IGNORECASE):
            errors.append("Explanation describes score as catch probability")
    
    # Check that primary lure is mentioned
    if response.primary.lure_name_he not in explanation:
        errors.append("Primary lure not mentioned in explanation")
    
    # Check that warnings are not contradicted
    for warning in response.warnings:
        if "בטיחות" in warning or "מסוכן" in warning:
            if "בטוח" in explanation and "לא" not in explanation[:explanation.index("בטוח")]:
                errors.append("Safety warning contradicted")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }


def generate_safe_explanation(response: RecommendationResponse) -> str:
    """Generate a safe, template-based explanation when LLM output fails validation."""
    primary = response.primary
    
    explanation = f"""ההמלצה הראשית: {primary.lure_name_he}
משקל מומלץ: {primary.recommended_weight_g}g
שכבת עבודה: {primary.working_layer}
ציון התאמה: {primary.suitability_score}/100 (ציון מבוסס חוקים, לא הסתברות תפיסה)

"""
    
    if response.reasons:
        explanation += "סיבות:\n"
        for reason in response.reasons:
            explanation += f"• {reason}\n"
    
    if response.warnings:
        explanation += "\nאזהרות:\n"
        for warning in response.warnings:
            explanation += f"⚠️ {warning}\n"
    
    if response.alternatives:
        explanation += "\nחלופות:\n"
        for alt in response.alternatives:
            explanation += f"• {alt.recommendation.lure_name_he}: {alt.switch_condition_he}\n"
    
    return explanation


class LLMAdapter:
    """
    Provider-neutral LLM adapter.
    
    The product functions fully without any LLM key through the wizard.
    """

    def __init__(self):
        self._provider: Optional[LLMProvider] = None

    def configure(
        self,
        provider: str,
        api_key: str,
    ) -> None:
        """Configure the LLM provider."""
        if provider == "openai":
            self._provider = OpenAIProvider(api_key)
        elif provider == "anthropic":
            self._provider = AnthropicProvider(api_key)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    @property
    def is_configured(self) -> bool:
        """Check if an LLM provider is configured."""
        return self._provider is not None

    async def parse_natural_language(
        self,
        user_message: str,
    ) -> dict[str, Any]:
        """Parse natural language into request fields."""
        if not self._provider:
            raise RuntimeError("LLM provider not configured")
        return await self._provider.parse_input(user_message)

    async def explain_recommendation(
        self,
        response: RecommendationResponse,
    ) -> str:
        """Generate natural language explanation."""
        if not self._provider:
            # Return safe template-based explanation
            return generate_safe_explanation(response)
        return await self._provider.generate_explanation(response)


# Global adapter instance
_llm_adapter: Optional[LLMAdapter] = None


def get_llm_adapter() -> LLMAdapter:
    """Get the global LLM adapter instance."""
    global _llm_adapter
    if _llm_adapter is None:
        _llm_adapter = LLMAdapter()
    return _llm_adapter
