"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {
        "name": "Mediterranean Shore Fishing Expert",
        "version": "1.0.0",
        "docs": "/docs",
    }
