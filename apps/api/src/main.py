"""FastAPI application entry point."""

import copy
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field

from src.config import get_settings
from src.routers import admin, catalog, feedback, forecast, recommendations
from src.services.database import init_db
from src.services.knowledge import load_knowledge

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ── Typed response models for health/root ────────────────────────────
class HealthResponse(BaseModel):
    status: str = Field(..., description="Service health status")
    version: str = Field(..., description="API version")


class RootResponse(BaseModel):
    name: str = Field(..., description="API name")
    version: str = Field(..., description="API version")
    docs: str = Field(..., description="Documentation URL")


# ── OpenAPI 3.1 → 3.0.3 post-processor for ChatGPT Actions ─────────
def _downgrade_schema(obj: Any) -> Any:
    """Walk the OpenAPI spec and convert 3.1-only constructs to 3.0.3.

    Transformations applied:
    1. ``anyOf: [{type: X, ...}, {type: "null"}]`` → ``{type: X, ..., nullable: true}``
    2. Remove ``prefixItems`` (leftover tuple schemas) and add ``items``
    3. Remove top-level ``webhooks`` key (unused, not in 3.0)
    4. Collapse single-element ``anyOf`` wrappers
    """
    if isinstance(obj, list):
        return [_downgrade_schema(v) for v in obj]
    if not isinstance(obj, dict):
        return obj

    obj = {k: _downgrade_schema(v) for k, v in obj.items()}

    # Handle anyOf nullable pattern:
    #   anyOf: [{type: "string"}, {type: "null"}]  →  type: "string", nullable: true
    if "anyOf" in obj and isinstance(obj["anyOf"], list):
        variants = obj["anyOf"]
        non_null = [v for v in variants if v.get("type") != "null"]
        has_null = any(v.get("type") == "null" for v in variants)

        if has_null and len(non_null) == 1:
            merged = dict(non_null[0])
            merged["nullable"] = True
            # Preserve surrounding keys (description, title, default, etc.)
            for k, v in obj.items():
                if k != "anyOf":
                    merged.setdefault(k, v)
            return merged
        if len(non_null) == 1 and not has_null:
            # Single-element anyOf — just unwrap
            merged = dict(non_null[0])
            for k, v in obj.items():
                if k != "anyOf":
                    merged.setdefault(k, v)
            return merged

    # Handle prefixItems (tuple schema) — shouldn't exist after our
    # tuple→list conversion, but handle defensively
    if "prefixItems" in obj:
        prefix = obj.pop("prefixItems")
        if prefix and "items" not in obj:
            # Use the first element's schema as the items schema
            obj["items"] = prefix[0]
        obj["type"] = "array"

    return obj


def custom_openapi() -> dict[str, Any]:
    """Generate an OpenAPI 3.0.3 spec compatible with ChatGPT Actions."""
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Deep-copy so post-processing doesn't mutate cached internals
    schema = copy.deepcopy(schema)

    # Downgrade to 3.0.3
    schema["openapi"] = "3.0.3"
    schema.pop("webhooks", None)

    # Walk and transform all schema constructs
    schema = _downgrade_schema(schema)

    app.openapi_schema = schema
    return schema


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    logger.info("Starting Mediterranean Shore Fishing Expert API...")
    
    # Initialize database
    await init_db()
    
    # Load knowledge base
    await load_knowledge()
    
    logger.info("API startup complete")
    yield
    
    logger.info("Shutting down API...")


app = FastAPI(
    title="Mediterranean Shore Fishing Expert",
    description="Deterministic lure recommendation engine for shore fishing in Israel's Mediterranean coast",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Override the default OpenAPI generator
app.openapi = custom_openapi  # type: ignore[method-assign]

# CORS middleware — restrict to configured origins
_cors_origins = [
    o.strip()
    for o in (settings.cors_allowed_origins or "").split(",")
    if o.strip()
] or ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Include routers
app.include_router(recommendations.router, prefix="/api/v1", tags=["recommendations"])
app.include_router(catalog.router, prefix="/api/v1/catalog", tags=["catalog"])
app.include_router(forecast.router, prefix="/api/v1", tags=["forecast"])
app.include_router(feedback.router, prefix="/api/v1", tags=["feedback"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="healthy", version="1.0.0")


@app.get("/", response_model=RootResponse)
async def root() -> RootResponse:
    """Root endpoint."""
    return RootResponse(
        name="Mediterranean Shore Fishing Expert",
        version="1.0.0",
        docs="/docs",
    )
