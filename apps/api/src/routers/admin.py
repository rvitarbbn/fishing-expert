"""Admin API router for rule and knowledge management.

Every endpoint requires a valid admin JWT (``Authorization: Bearer <token>``).
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import require_admin
from src.models.admin import AdminUser, Rule, RuleStatus, RuleVersion
from src.services.database import get_db
from src.services.knowledge import reload_db_rules

logger = logging.getLogger(__name__)

# All routes in this router require admin authentication
router = APIRouter(dependencies=[Depends(require_admin)])


class RuleCreate(BaseModel):
    """Schema for creating a new rule."""
    id: str = Field(..., description="Unique rule ID")
    priority: int = Field(default=50, ge=0, le=100)
    when_conditions: dict[str, Any] = Field(..., description="Rule conditions")
    candidate: Optional[str] = Field(None, description="Target lure type")
    score_delta: int = Field(default=0, description="Score adjustment")
    exclude: bool = Field(default=False, description="Whether this is an exclusion rule")
    reason_he: str = Field(..., description="Hebrew reason text")


class RuleUpdate(BaseModel):
    """Schema for updating a rule."""
    priority: Optional[int] = Field(None, ge=0, le=100)
    when_conditions: Optional[dict[str, Any]] = None
    candidate: Optional[str] = None
    score_delta: Optional[int] = None
    exclude: Optional[bool] = None
    reason_he: Optional[str] = None
    enabled: Optional[bool] = None


class RuleResponse(BaseModel):
    """Schema for rule response."""
    id: str
    enabled: bool
    priority: int
    when_conditions: dict[str, Any]
    candidate: Optional[str]
    score_delta: int
    exclude: bool
    reason_he: str
    status: str
    created_at: datetime
    updated_at: datetime


@router.get("/rules", response_model=list[RuleResponse])
async def list_rules(
    status: Optional[str] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
) -> list[RuleResponse]:
    """List all rules, optionally filtered by status."""
    query = select(Rule)
    
    if status:
        try:
            status_enum = RuleStatus(status)
            query = query.where(Rule.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    result = await db.execute(query.order_by(Rule.priority.desc()))
    rules = result.scalars().all()
    
    return [
        RuleResponse(
            id=rule.id,
            enabled=rule.enabled,
            priority=rule.priority,
            when_conditions=rule.when_conditions,
            candidate=rule.candidate,
            score_delta=rule.score_delta,
            exclude=rule.exclude,
            reason_he=rule.reason_he,
            status=rule.status.value,
            created_at=rule.created_at,
            updated_at=rule.updated_at,
        )
        for rule in rules
    ]


@router.post("/rules", response_model=RuleResponse)
async def create_rule(
    rule_data: RuleCreate,
    db: AsyncSession = Depends(get_db),
) -> RuleResponse:
    """
    Create a new rule in draft status.
    
    Rules must be validated and published before taking effect.
    """
    # Check for duplicate ID
    existing = await db.execute(select(Rule).where(Rule.id == rule_data.id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Rule ID '{rule_data.id}' already exists")
    
    rule = Rule(
        id=rule_data.id,
        priority=rule_data.priority,
        when_conditions=rule_data.when_conditions,
        candidate=rule_data.candidate,
        score_delta=rule_data.score_delta,
        exclude=rule_data.exclude,
        reason_he=rule_data.reason_he,
        status=RuleStatus.DRAFT,
    )
    
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    
    return RuleResponse(
        id=rule.id,
        enabled=rule.enabled,
        priority=rule.priority,
        when_conditions=rule.when_conditions,
        candidate=rule.candidate,
        score_delta=rule.score_delta,
        exclude=rule.exclude,
        reason_he=rule.reason_he,
        status=rule.status.value,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


@router.put("/rules/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: str,
    rule_data: RuleUpdate,
    db: AsyncSession = Depends(get_db),
) -> RuleResponse:
    """
    Update a rule. Published rules return to draft status on update.
    """
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    # Store version before update
    version_count = await db.execute(
        select(RuleVersion).where(RuleVersion.rule_id == rule_id)
    )
    version_num = len(version_count.scalars().all()) + 1
    
    version = RuleVersion(
        rule_id=rule_id,
        version=version_num,
        rule_snapshot={
            "priority": rule.priority,
            "when_conditions": rule.when_conditions,
            "candidate": rule.candidate,
            "score_delta": rule.score_delta,
            "exclude": rule.exclude,
            "reason_he": rule.reason_he,
            "enabled": rule.enabled,
            "status": rule.status.value,
        },
    )
    db.add(version)
    
    # Apply updates
    if rule_data.priority is not None:
        rule.priority = rule_data.priority
    if rule_data.when_conditions is not None:
        rule.when_conditions = rule_data.when_conditions
    if rule_data.candidate is not None:
        rule.candidate = rule_data.candidate
    if rule_data.score_delta is not None:
        rule.score_delta = rule_data.score_delta
    if rule_data.exclude is not None:
        rule.exclude = rule_data.exclude
    if rule_data.reason_he is not None:
        rule.reason_he = rule_data.reason_he
    if rule_data.enabled is not None:
        rule.enabled = rule_data.enabled
    
    # Return to draft if was published
    if rule.status == RuleStatus.PUBLISHED:
        rule.status = RuleStatus.DRAFT
    
    await db.commit()
    await db.refresh(rule)
    
    return RuleResponse(
        id=rule.id,
        enabled=rule.enabled,
        priority=rule.priority,
        when_conditions=rule.when_conditions,
        candidate=rule.candidate,
        score_delta=rule.score_delta,
        exclude=rule.exclude,
        reason_he=rule.reason_he,
        status=rule.status.value,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


@router.post("/rules/{rule_id}/validate")
async def validate_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Validate a rule before publishing.
    
    Checks for:
    - Valid condition keys
    - Valid candidate lure type
    - No duplicate rule IDs
    """
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    errors = []
    
    # Validate condition keys
    valid_condition_keys = {
        "target_fish", "foam", "water_clarity", "surface_activity",
        "birds_diving", "wind_strength", "current_strength", "structure",
        "time_bucket", "activity_distance", "desired_layer", "sea_state",
        "candidate_weight_above_rod_max", "candidate_weight_below_rod_min_materially",
    }
    
    for key in rule.when_conditions.keys():
        if key not in valid_condition_keys:
            errors.append(f"Unknown condition key: {key}")
    
    # Validate candidate
    valid_candidates = {
        "minnow", "heavy_minnow", "popper", "pencil", "stickbait",
        "metal_jig", "micro_jig", "soft_plastic", "vibe", "blade",
    }
    
    if rule.candidate and rule.candidate not in valid_candidates:
        errors.append(f"Unknown candidate: {rule.candidate}")
    
    if errors:
        return {"valid": False, "errors": errors}
    
    rule.status = RuleStatus.VALIDATED
    await db.commit()
    
    return {"valid": True, "message": "Rule validated successfully"}


@router.post("/rules/{rule_id}/publish")
async def publish_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Publish a validated rule to production.
    """
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    if rule.status != RuleStatus.VALIDATED:
        raise HTTPException(
            status_code=400,
            detail=f"Rule must be validated before publishing. Current status: {rule.status.value}",
        )
    
    rule.status = RuleStatus.PUBLISHED
    rule.published_at = datetime.utcnow()
    await db.commit()

    # Refresh in-memory rules so the engine picks up the change
    await reload_db_rules()
    logger.info("Rule %s published; in-memory rules refreshed", rule_id)

    return {"message": f"Rule {rule_id} published successfully"}


@router.post("/rules/{rule_id}/rollback")
async def rollback_rule(
    rule_id: str,
    version: int = Query(..., description="Version to rollback to"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Rollback a rule to a previous version.
    """
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    # Find version
    version_result = await db.execute(
        select(RuleVersion).where(
            RuleVersion.rule_id == rule_id,
            RuleVersion.version == version,
        )
    )
    rule_version = version_result.scalar_one_or_none()
    
    if not rule_version:
        raise HTTPException(status_code=404, detail=f"Version {version} not found")
    
    # Apply snapshot
    snapshot = rule_version.rule_snapshot
    rule.priority = snapshot["priority"]
    rule.when_conditions = snapshot["when_conditions"]
    rule.candidate = snapshot.get("candidate")
    rule.score_delta = snapshot["score_delta"]
    rule.exclude = snapshot["exclude"]
    rule.reason_he = snapshot["reason_he"]
    rule.enabled = snapshot["enabled"]
    rule.status = RuleStatus.DRAFT  # Rollback returns to draft
    
    await db.commit()

    # A previously-published rule is now draft; refresh engine rules
    await reload_db_rules()

    return {"message": f"Rule {rule_id} rolled back to version {version}"}


@router.get("/rules/export")
async def export_rules(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Export all published rules as JSON."""
    result = await db.execute(
        select(Rule).where(Rule.status == RuleStatus.PUBLISHED)
    )
    rules = result.scalars().all()
    
    return {
        "version": datetime.utcnow().strftime("%Y%m%d%H%M%S"),
        "exported_at": datetime.utcnow().isoformat(),
        "rules": [
            {
                "id": rule.id,
                "enabled": rule.enabled,
                "priority": rule.priority,
                "when": rule.when_conditions,
                "candidate": rule.candidate,
                "effect": {
                    "score_delta": rule.score_delta,
                    "exclude": rule.exclude,
                },
                "reason_he": rule.reason_he,
            }
            for rule in rules
        ],
    }


@router.post("/rules/import")
async def import_rules(
    rules_data: dict,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Import rules from JSON.
    
    Imported rules are created in draft status and require validation.
    """
    rules = rules_data.get("rules", [])
    imported = 0
    skipped = 0
    
    for rule_dict in rules:
        rule_id = rule_dict.get("id")
        if not rule_id:
            skipped += 1
            continue
        
        # Check if exists
        existing = await db.execute(select(Rule).where(Rule.id == rule_id))
        if existing.scalar_one_or_none():
            skipped += 1
            continue
        
        effect = rule_dict.get("effect", {})
        rule = Rule(
            id=rule_id,
            enabled=rule_dict.get("enabled", True),
            priority=rule_dict.get("priority", 50),
            when_conditions=rule_dict.get("when", {}),
            candidate=rule_dict.get("candidate"),
            score_delta=effect.get("score_delta", 0),
            exclude=effect.get("exclude", False),
            reason_he=rule_dict.get("reason_he", ""),
            status=RuleStatus.DRAFT,
        )
        db.add(rule)
        imported += 1
    
    await db.commit()

    # Refresh engine in case imported rules affect published set
    await reload_db_rules()

    return {
        "imported": imported,
        "skipped": skipped,
        "message": f"Imported {imported} rules, skipped {skipped}",
    }
