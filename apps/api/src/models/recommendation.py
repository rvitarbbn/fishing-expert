"""Recommendation audit model for immutable recommendation storage."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.services.database import Base


class RecommendationAudit(Base):
    """
    Immutable audit record of recommendations.
    
    Stores the complete recommendation for traceability and analysis.
    """

    __tablename__ = "recommendation_audits"

    # UUID primary key — unique per request instance
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    # Deterministic fingerprint — same normalised input & rules => same value
    recommendation_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    
    # Request data
    target_fish: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    location_name: Mapped[str] = mapped_column(String(256), nullable=False)
    fishing_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Normalized conditions (JSON)
    normalized_conditions: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    
    # Equipment
    rod_cast_min_g: Mapped[float] = mapped_column(nullable=False)
    rod_cast_max_g: Mapped[float] = mapped_column(nullable=False)
    
    # Primary recommendation
    primary_lure_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    primary_weight_g: Mapped[float] = mapped_column(nullable=True)
    primary_score: Mapped[int] = mapped_column(nullable=False)
    
    # Full response (JSON)
    full_response: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    
    # Versions
    rules_version: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    knowledge_version: Mapped[str] = mapped_column(String(32), nullable=False)
    
    # Data quality
    completeness_score: Mapped[float] = mapped_column(nullable=False)
    data_source: Mapped[str] = mapped_column(String(32), nullable=False)
    
    # Warnings
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)

    def __repr__(self) -> str:
        return f"RecommendationAudit({self.id}, {self.target_fish}, {self.primary_lure_type})"
