"""Feedback API router."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.feedback import FeedbackRecord
from src.models.recommendation import RecommendationAudit
from src.schemas.feedback import FeedbackRequest, FeedbackResponse
from src.services.database import get_db

router = APIRouter()


@router.post(
    "/recommendations/{recommendation_id}/feedback",
    response_model=FeedbackResponse,
)
async def submit_feedback(
    recommendation_id: str,
    feedback: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    """
    Submit feedback on a recommendation.
    
    Feedback is stored for analysis but CANNOT directly modify
    production rules. Rule changes require human review.
    """
    # Verify recommendation exists
    result = await db.execute(
        select(RecommendationAudit).where(RecommendationAudit.id == recommendation_id)
    )
    audit = result.scalar_one_or_none()
    
    if not audit:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    # Verify feedback matches recommendation ID
    if feedback.recommendation_id != recommendation_id:
        raise HTTPException(
            status_code=400,
            detail="Feedback recommendation_id must match URL parameter",
        )
    
    # Create feedback record
    feedback_id = f"fb_{uuid.uuid4().hex[:16]}"
    
    record = FeedbackRecord(
        id=feedback_id,
        recommendation_id=recommendation_id,
        recommendation_followed=feedback.recommendation_followed,
        lure_used=feedback.lure_used,
        strike_seen=feedback.strike_seen,
        fish_caught=feedback.fish_caught,
        species_reported=feedback.species_reported,
        free_text=feedback.free_text,
        consent_to_research=feedback.consent_to_research,
    )
    
    db.add(record)
    await db.commit()
    
    return FeedbackResponse(
        feedback_id=feedback_id,
        recommendation_id=recommendation_id,
        received_at=datetime.utcnow(),
        message="Feedback received successfully. Thank you for contributing!",
    )
