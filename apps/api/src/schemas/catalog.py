"""Catalog schemas for fish, lures, colors, and retrieves."""

from typing import Optional

from pydantic import BaseModel, Field


class FishSpecies(BaseModel):
    """Fish species information."""

    id: str = Field(..., description="Unique species identifier")
    name_he: str = Field(..., description="Hebrew name")
    name_en: str = Field(..., description="English name")
    preferred_lures: list[str] = Field(..., description="List of preferred lure type IDs")
    active_times: list[str] = Field(..., description="Active time periods")
    habitats: list[str] = Field(..., description="Preferred habitats")
    seasonality_note: str = Field(..., description="Seasonality information")
    legal_status: str = Field(
        ..., description="Legal status: runtime_check_required, protected, etc."
    )
    confidence: str = Field(..., description="Data confidence level")


class Lure(BaseModel):
    """Lure type information."""

    id: str = Field(..., description="Unique lure type identifier")
    name_he: str = Field(..., description="Hebrew name")
    length_cm: tuple[float, float] = Field(..., description="Length range in cm")
    weight_g: tuple[float, float] = Field(..., description="Weight range in grams")
    layers: list[str] = Field(..., description="Working water layers")
    retrieves: list[str] = Field(..., description="Compatible retrieve methods")
    brand_neutral: bool = Field(True, description="Whether recommendation is brand-neutral")
    notes_he: Optional[str] = Field(None, description="Notes in Hebrew")


class RetrieveMethod(BaseModel):
    """Retrieve method information."""

    id: str = Field(..., description="Unique retrieve method identifier")
    name_he: str = Field(..., description="Hebrew name")
    steps_he: list[str] = Field(..., description="Steps in Hebrew")
    use_when: list[str] = Field(..., description="Conditions when to use this retrieve")


class ColorFamily(BaseModel):
    """Color family information."""

    id: str = Field(..., description="Unique color family identifier")
    name_he: str = Field(..., description="Hebrew name")
    best_for: list[str] = Field(..., description="Conditions where this color works best")


class LocationSeed(BaseModel):
    """Seed location information."""

    id: str = Field(..., description="Unique location identifier")
    name_he: str = Field(..., description="Hebrew name")
    structure_profile: str = Field(..., description="Structure profile type")
    coordinates: Optional[tuple[float, float]] = Field(None, description="Lat/lon coordinates")
    notes: str = Field(..., description="Notes about the location")
    verified: bool = Field(False, description="Whether location data is verified")


class EquipmentClass(BaseModel):
    """Equipment class information."""

    id: str = Field(..., description="Equipment class identifier")
    cast_min_g: float = Field(..., description="Minimum casting weight")
    cast_max_g: float = Field(..., description="Maximum casting weight")
    recommended_working_max_g: float = Field(..., description="Recommended working maximum")
