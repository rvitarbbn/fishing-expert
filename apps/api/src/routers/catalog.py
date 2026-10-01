"""Catalog API router for fish, lures, and other reference data."""

from fastapi import APIRouter

from src.schemas.catalog import ColorFamily, FishSpecies, Lure, RetrieveMethod
from src.services.knowledge import get_knowledge_base

router = APIRouter()


@router.get("/fish", response_model=list[FishSpecies])
async def list_fish() -> list[FishSpecies]:
    """
    Return all enabled target fish species.
    
    Legal status requires runtime verification against official sources.
    """
    kb = get_knowledge_base()
    fish_data = kb.get_all_fish()
    
    return [
        FishSpecies(
            id=fish_id,
            name_he=data.get("name_he", fish_id),
            name_en=data.get("name_en", fish_id),
            preferred_lures=data.get("preferred_lures", []),
            active_times=data.get("active_times", []),
            habitats=data.get("habitats", []),
            seasonality_note=data.get("seasonality_note", ""),
            legal_status=data.get("legal_status", "runtime_check_required"),
            confidence=data.get("confidence", "seed_expert_heuristic"),
        )
        for fish_id, data in fish_data.items()
    ]


@router.get("/lures", response_model=list[Lure])
async def list_lures() -> list[Lure]:
    """
    Return brand-neutral lure catalog.
    
    Recommendations are based on lure characteristics, not specific brands.
    """
    kb = get_knowledge_base()
    lure_data = kb.get_all_lures()
    
    return [
        Lure(
            id=lure_id,
            name_he=data.get("name_he", lure_id),
            length_cm=tuple(data.get("length_cm", [0, 0])),
            weight_g=tuple(data.get("weight_g", [0, 0])),
            layers=data.get("layers", []),
            retrieves=data.get("retrieves", []),
            brand_neutral=data.get("brand_neutral", True),
            notes_he=data.get("notes_he"),
        )
        for lure_id, data in lure_data.items()
    ]


@router.get("/retrieves", response_model=list[RetrieveMethod])
async def list_retrieves() -> list[RetrieveMethod]:
    """Return all retrieve methods with Hebrew instructions."""
    kb = get_knowledge_base()
    retrieve_data = kb.get_all_retrieves()
    
    return [
        RetrieveMethod(
            id=retrieve_id,
            name_he=data.get("name_he", retrieve_id),
            steps_he=data.get("steps_he", []),
            use_when=data.get("use_when", []),
        )
        for retrieve_id, data in retrieve_data.items()
    ]


@router.get("/colors", response_model=list[ColorFamily])
async def list_colors() -> list[ColorFamily]:
    """Return all color families with usage recommendations."""
    kb = get_knowledge_base()
    color_data = kb.get_all_colors()
    
    return [
        ColorFamily(
            id=color_id,
            name_he=data.get("name_he", color_id),
            best_for=data.get("best_for", []),
        )
        for color_id, data in color_data.items()
    ]


@router.get("/locations")
async def list_locations() -> list[dict]:
    """
    Return seed location data.
    
    Location data is not verified and requires runtime validation
    for access, reserve boundaries, hazards, and legality.
    """
    kb = get_knowledge_base()
    location_data = kb.get_all_locations()
    
    return [
        {
            "id": loc_id,
            "name_he": data.get("name_he", loc_id),
            "structure_profile": data.get("structure_profile"),
            "coordinates": data.get("coordinates"),
            "notes": data.get("notes"),
            "verified": data.get("verified", False),
        }
        for loc_id, data in location_data.items()
    ]


@router.get("/seed-status")
async def seed_status() -> dict:
    """
    Diagnostic endpoint — shows how much seed data is loaded.

    Returns counts for every knowledge-base section and a boolean
    ``loaded`` flag that is ``true`` when fish + lures are present.
    """
    kb = get_knowledge_base()
    return kb.seed_status()
