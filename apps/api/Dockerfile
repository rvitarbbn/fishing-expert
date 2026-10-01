FROM python:3.12-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Copy all source BEFORE pip install ──────────────────────────────
# Hatchling needs pyproject.toml, README.md, and the src/ package
# at metadata-preparation time.  Copying everything first avoids the
# "Readme file does not exist" error and ensures the installed wheel
# contains the real source (no stale stub in site-packages).
COPY pyproject.toml README.md alembic.ini ./
COPY src/ src/
COPY migrations/ migrations/

# Install (non-editable) with production extras
RUN pip install --no-cache-dir ".[postgres]"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
