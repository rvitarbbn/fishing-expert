FROM python:3.12-slim

# Build context must be the REPO ROOT, not apps/api/.
#   docker build -f apps/api/Dockerfile .
#   (docker-compose and Render are configured accordingly)

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Copy API source (paths relative to repo root) ──────────────────
COPY apps/api/pyproject.toml apps/api/README.md apps/api/alembic.ini ./
COPY apps/api/src/ src/
COPY apps/api/migrations/ migrations/

# ── Bake seed knowledge into the image ──────────────────────────────
COPY packages/knowledge/ packages/knowledge/

# ── Install (non-editable) with production extras ───────────────────
RUN pip install --no-cache-dir ".[postgres]"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
