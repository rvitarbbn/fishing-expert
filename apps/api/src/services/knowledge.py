"""Knowledge base service for loading and accessing seed data.

Rules are merged from two sources:
1. Seed JSON files (``packages/knowledge/rules.json``)
2. DB-published rules (``Rule`` rows with ``status == PUBLISHED``)

DB rules are loaded on startup and refreshed whenever the admin
publishes, rollbacks, or imports rules (via ``reload_db_rules``).
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Global knowledge base instance
_knowledge_base: Optional["KnowledgeBase"] = None


class KnowledgeBase:
    """
    In-memory knowledge base loaded from JSON seed files and DB-published rules.
    
    Provides versioned access to:
    - Fish species
    - Lure types
    - Rules  (seed + DB-published, merged)
    - Colors
    - Retrieves
    - Locations
    - Equipment classes
    - Sea condition matrix
    """

    def __init__(self):
        self.fish: dict[str, dict[str, Any]] = {}
        self.lures: dict[str, dict[str, Any]] = {}
        self._seed_rules: list[dict[str, Any]] = []
        self._db_rules: list[dict[str, Any]] = []
        self.colors: dict[str, dict[str, Any]] = {}
        self.retrieves: dict[str, dict[str, Any]] = {}
        self.locations: dict[str, dict[str, Any]] = {}
        self.equipment_classes: dict[str, dict[str, Any]] = {}
        self.sea_condition_matrix: list[dict[str, Any]] = []
        
        self.rules_version: str = "1.0.0"
        self.knowledge_version: str = "1.0.0"
        self._scoring_start: int = 50

    def load_from_directory(self, knowledge_dir: Path) -> None:
        """Load all knowledge files from a directory."""
        logger.info(f"Loading knowledge from {knowledge_dir}")
        
        # Load fish
        fish_file = knowledge_dir / "fish.json"
        if fish_file.exists():
            data = json.loads(fish_file.read_text(encoding="utf-8"))
            self.knowledge_version = data.get("version", "1.0.0")
            for species in data.get("species", []):
                self.fish[species["id"]] = species
            logger.info(f"Loaded {len(self.fish)} fish species")
        
        # Load lures
        lures_file = knowledge_dir / "lures.json"
        if lures_file.exists():
            data = json.loads(lures_file.read_text(encoding="utf-8"))
            for lure in data.get("lures", []):
                self.lures[lure["id"]] = lure
            logger.info(f"Loaded {len(self.lures)} lure types")
        
        # Load seed rules
        rules_file = knowledge_dir / "rules.json"
        if rules_file.exists():
            data = json.loads(rules_file.read_text(encoding="utf-8"))
            self.rules_version = data.get("version", "1.0.0")
            self._scoring_start = data.get("scoring_start", 50)
            self._seed_rules = data.get("rules", [])
            logger.info(f"Loaded {len(self._seed_rules)} seed rules")
        
        # Load colors
        colors_file = knowledge_dir / "colors.json"
        if colors_file.exists():
            data = json.loads(colors_file.read_text(encoding="utf-8"))
            for color in data.get("families", []):
                self.colors[color["id"]] = color
            logger.info(f"Loaded {len(self.colors)} color families")
        
        # Load retrieves
        retrieves_file = knowledge_dir / "retrieves.json"
        if retrieves_file.exists():
            data = json.loads(retrieves_file.read_text(encoding="utf-8"))
            for retrieve in data.get("retrieves", []):
                self.retrieves[retrieve["id"]] = retrieve
            logger.info(f"Loaded {len(self.retrieves)} retrieve methods")
        
        # Load locations
        locations_file = knowledge_dir / "locations_seed.json"
        if locations_file.exists():
            data = json.loads(locations_file.read_text(encoding="utf-8"))
            for location in data.get("locations", []):
                self.locations[location["id"]] = location
            logger.info(f"Loaded {len(self.locations)} locations")
        
        # Load equipment
        equipment_file = knowledge_dir / "equipment.json"
        if equipment_file.exists():
            data = json.loads(equipment_file.read_text(encoding="utf-8"))
            for eq_class in data.get("rod_classes", []):
                self.equipment_classes[eq_class["id"]] = eq_class
            logger.info(f"Loaded {len(self.equipment_classes)} equipment classes")
        
        # Load sea condition matrix
        matrix_file = knowledge_dir / "sea_condition_matrix.json"
        if matrix_file.exists():
            data = json.loads(matrix_file.read_text(encoding="utf-8"))
            self.sea_condition_matrix = data.get("rows", [])
            logger.info(f"Loaded {len(self.sea_condition_matrix)} sea condition rows")

    def get_fish(self, fish_id: str) -> Optional[dict[str, Any]]:
        """Get fish species by ID."""
        return self.fish.get(fish_id)

    def get_all_fish(self) -> dict[str, dict[str, Any]]:
        """Get all fish species."""
        return self.fish

    def get_lure(self, lure_id: str) -> Optional[dict[str, Any]]:
        """Get lure type by ID."""
        return self.lures.get(lure_id)

    def get_all_lures(self) -> dict[str, dict[str, Any]]:
        """Get all lure types."""
        return self.lures

    @property
    def rules(self) -> list[dict[str, Any]]:
        """Combined seed + DB rules (backward-compat property)."""
        return self.get_all_rules()

    def get_all_rules(self) -> list[dict[str, Any]]:
        """Return merged rules: seed rules overlaid by DB-published rules.

        DB rules override seed rules with the same ``id``.
        """
        if not self._db_rules:
            return list(self._seed_rules)

        db_ids = {r["id"] for r in self._db_rules}
        merged = [r for r in self._seed_rules if r.get("id") not in db_ids]
        merged.extend(self._db_rules)
        return merged

    def set_db_rules(self, db_rules: list[dict[str, Any]]) -> None:
        """Replace the in-memory set of DB-published rules (called on reload)."""
        self._db_rules = db_rules
        logger.info("Reloaded %d DB-published rules into knowledge base", len(db_rules))

    def get_color(self, color_id: str) -> Optional[dict[str, Any]]:
        """Get color family by ID."""
        return self.colors.get(color_id)

    def get_all_colors(self) -> dict[str, dict[str, Any]]:
        """Get all color families."""
        return self.colors

    def get_retrieve(self, retrieve_id: str) -> Optional[dict[str, Any]]:
        """Get retrieve method by ID."""
        return self.retrieves.get(retrieve_id)

    def get_all_retrieves(self) -> dict[str, dict[str, Any]]:
        """Get all retrieve methods."""
        return self.retrieves

    def get_location(self, location_id: str) -> Optional[dict[str, Any]]:
        """Get location by ID."""
        return self.locations.get(location_id)

    def get_all_locations(self) -> dict[str, dict[str, Any]]:
        """Get all locations."""
        return self.locations

    def get_scoring_start(self) -> int:
        """Get the starting score for candidates."""
        return self._scoring_start


async def load_knowledge() -> None:
    """Load knowledge base from seed files, then overlay DB-published rules."""
    global _knowledge_base
    
    _knowledge_base = KnowledgeBase()
    
    # Try multiple possible locations for knowledge files
    possible_paths = [
        Path(__file__).parent.parent.parent.parent / "packages" / "knowledge",
        Path("/app/packages/knowledge"),
        Path("packages/knowledge"),
    ]
    
    for path in possible_paths:
        if path.exists():
            _knowledge_base.load_from_directory(path)
            break
    else:
        logger.warning("No knowledge directory found, using empty knowledge base")

    # Load published rules from DB (best-effort at startup)
    await reload_db_rules()


async def reload_db_rules() -> None:
    """Fetch all published rules from the DB and refresh the knowledge base.

    Called on startup and after admin publish / rollback / import actions.
    """
    global _knowledge_base
    if _knowledge_base is None:
        return

    try:
        from sqlalchemy import select

        from src.models.admin import Rule, RuleStatus
        from src.services.database import async_session_maker

        async with async_session_maker() as session:
            result = await session.execute(
                select(Rule).where(Rule.status == RuleStatus.PUBLISHED, Rule.enabled == True)
            )
            rows = result.scalars().all()

        db_rules = [
            {
                "id": r.id,
                "enabled": r.enabled,
                "priority": r.priority,
                "when": r.when_conditions,
                "candidate": r.candidate,
                "effect": {"score_delta": r.score_delta, "exclude": r.exclude},
                "reason_he": r.reason_he,
            }
            for r in rows
        ]
        _knowledge_base.set_db_rules(db_rules)
    except Exception:
        logger.warning("Could not load DB rules (DB may not be ready yet)", exc_info=True)


def get_knowledge_base() -> KnowledgeBase:
    """Get the global knowledge base instance."""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = KnowledgeBase()
    return _knowledge_base
