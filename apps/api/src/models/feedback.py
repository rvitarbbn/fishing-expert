"""Feedback model for user feedback storage."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.services.database import Base


class FeedbackRecord(Base):
    """
    User feedback on recommendations.
    
    Feedback cannot directly modify production rules.
    """

    __tablename__ = "feedback_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    recommendation_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("recommendation_audits.id"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    
    # Feedback data
    recommendation_followed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    lure_used: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    strike_seen: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    fish_caught: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    species_reported: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    free_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Consent
    consent_to_research: Mapped[bool] = mapped_column(Boolean, default=False)

    def __repr__(self) -> str:
        return f"FeedbackRecord({self.id}, rec={self.recommendation_id})"
