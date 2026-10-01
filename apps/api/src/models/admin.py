"""Admin models for rule and knowledge management."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, Enum as SQLEnum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.services.database import Base


class RuleStatus(str, Enum):
    """Rule lifecycle status."""
    DRAFT = "draft"
    PENDING_VALIDATION = "pending_validation"
    VALIDATED = "validated"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Rule(Base):
    """
    Rule definition for the decision engine.
    
    Rules go through draft -> validate -> publish workflow.
    """

    __tablename__ = "rules"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    
    # Rule definition
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(default=50)
    
    # Conditions (JSON)
    when_conditions: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    
    # Target candidate
    candidate: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    # Effect
    score_delta: Mapped[int] = mapped_column(default=0)
    exclude: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Reason
    reason_he: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Status
    status: Mapped[RuleStatus] = mapped_column(
        SQLEnum(RuleStatus), default=RuleStatus.DRAFT
    )
    
    # Audit
    created_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    published_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    def __repr__(self) -> str:
        return f"Rule({self.id}, status={self.status})"


class RuleVersion(Base):
    """
    Version history for rules.
    
    Maintains immutable history of rule changes.
    """

    __tablename__ = "rule_versions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    rule_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("rules.id"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    
    # Snapshot of rule at this version
    rule_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    
    # Change metadata
    changed_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    change_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"RuleVersion({self.rule_id}, v{self.version})"


class AdminUser(Base):
    """Admin user for rule management."""

    __tablename__ = "admin_users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:
        return f"AdminUser({self.username})"
