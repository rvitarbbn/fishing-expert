"""Recommendations API router."""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.engine.recommendation_engine import RecommendationEngine
from src.models.recommendation import RecommendationAudit
from src.schemas.recommendation import RecommendationRequest, RecommendationResponse
from src.services.database import get_db
from src.services.forecast import ForecastError, get_forecast_service
from src.services.knowledge import get_knowledge_base

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/recommendations", response_model=RecommendationResponse)
async def create_recommendation(
    request: RecommendationRequest,
    db: AsyncSession = Depends(get_db),
) -> RecommendationResponse:
    """
    Generate lure recommendations based on conditions and equipment.
    
    The recommendation engine is deterministic: same normalized inputs
    and rules version will always produce identical results.
    
    Suitability scores are rules-based compatibility measures,
    NOT catch probability predictions.
    """
    kb = get_knowledge_base()
    engine = RecommendationEngine(kb)
    forecast_service = get_forecast_service()
    
    # Fetch forecast if requested and location has coordinates
    forecast_data: Optional[dict] = None
    if request.use_forecast and request.location.latitude and request.location.longitude:
        try:
            forecast_response = await forecast_service.get_forecast(
                latitude=request.location.latitude,
                longitude=request.location.longitude,
                target_datetime=request.fishing_time,
            )
            forecast_data = {
                "marine": forecast_response.marine.model_dump(),
                "weather": forecast_response.weather.model_dump(),
                "provider": forecast_response.provider,
                "fetch_timestamp": forecast_response.fetch_timestamp.isoformat(),
                "confidence": forecast_response.confidence,
            }
        except ForecastError as e:
            logger.warning(f"Forecast fetch failed, proceeding without: {e}")
            # Continue without forecast - user can provide manual conditions
    
    try:
        response = engine.recommend(request, forecast_data)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Recommendation failed: {e}")
        raise HTTPException(status_code=500, detail="Recommendation generation failed")
    
    # Store audit record using a unique UUID as primary key so identical
    # deterministic recommendation IDs can coexist across requests.
    audit_persisted = True
    try:
        audit = RecommendationAudit(
            id=str(uuid.uuid4()),
            recommendation_fingerprint=response.recommendation_id,
            target_fish=request.target_fish,
            location_name=request.location.name,
            fishing_time=request.fishing_time,
            normalized_conditions=response.normalized_conditions,
            rod_cast_min_g=request.equipment.rod_cast_min_g,
            rod_cast_max_g=request.equipment.rod_cast_max_g,
            primary_lure_type=response.primary.lure_type,
            primary_weight_g=response.primary.recommended_weight_g,
            primary_score=response.primary.suitability_score,
            full_response=response.model_dump(mode="json"),
            rules_version=response.rules_version,
            knowledge_version=response.knowledge_version,
            completeness_score=response.data_quality.completeness_score,
            data_source=response.data_quality.data_source,
            warnings=response.warnings,
        )
        db.add(audit)
        await db.commit()
    except Exception as e:
        logger.error(f"Failed to store audit record: {e}", exc_info=True)
        audit_persisted = False
        await db.rollback()

    # If audit storage failed, add a header so the caller is aware
    if not audit_persisted:
        resp = JSONResponse(content=response.model_dump(mode="json"))
        resp.headers["X-Audit-Persisted"] = "false"
        return resp

    return response


@router.get("/recommendations/{recommendation_id}", response_model=RecommendationResponse)
async def get_recommendation(
    recommendation_id: str,
    db: AsyncSession = Depends(get_db),
) -> RecommendationResponse:
    """Retrieve a previous recommendation by audit UUID or deterministic fingerprint."""
    from sqlalchemy import or_, select

    result = await db.execute(
        select(RecommendationAudit)
        .where(
            or_(
                RecommendationAudit.id == recommendation_id,
                RecommendationAudit.recommendation_fingerprint == recommendation_id,
            )
        )
        .order_by(RecommendationAudit.created_at.desc())
        .limit(1)
    )
    audit = result.scalar_one_or_none()
    
    if not audit:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    return RecommendationResponse(**audit.full_response)
