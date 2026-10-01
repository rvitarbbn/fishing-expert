# Mediterranean Shore Fishing Expert

A production-ready application for shore fishing lure recommendations on Israel's Mediterranean coast.

## Features

- **Deterministic Recommendation Engine**: Rules-based lure selection that produces consistent results
- **Hebrew RTL UI**: Mobile-first, accessible interface in Hebrew
- **Open-Meteo Integration**: Marine and weather forecast with caching
- **Admin Management**: Draft, validate, publish workflow for rules
- **Audit Trail**: Immutable recommendation history

## Architecture

```
fishing-expert/
├── apps/
│   ├── api/          # FastAPI backend (Python 3.12)
│   └── web/          # Next.js frontend (TypeScript)
├── packages/
│   ├── knowledge/    # Versioned seed data (JSON)
│   └── openapi/      # Exported OpenAPI schema
├── docs/             # Documentation
└── docker-compose.yml
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 20+ (for local development)
- Python 3.12+ (for local development)

### Running with Docker

```bash
# Copy environment file
cp .env.example .env

# Start all services
docker-compose up -d

# Access the application
# Web: http://localhost:3000
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

### Local Development

**API:**
```bash
cd apps/api
pip install -e ".[dev]"
uvicorn src.main:app --reload
```

**Web:**
```bash
cd apps/web
npm install
npm run dev
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/recommendations` | POST | Generate lure recommendations |
| `/api/v1/recommendations/{id}` | GET | Retrieve a recommendation |
| `/api/v1/catalog/fish` | GET | List target fish species |
| `/api/v1/catalog/lures` | GET | List lure types |
| `/api/v1/forecast` | GET | Get marine/weather forecast |
| `/api/v1/recommendations/{id}/feedback` | POST | Submit feedback |

## Engine Pipeline

1. **Normalize** inputs into categorical conditions
2. **Enrich** with forecast data (optional)
3. **Generate** lure candidates from catalog
4. **Apply** soft rules as score deltas
5. **Apply** hard exclusions (weight, safety, legal)
6. **Select** compatible size/weight/color/retrieve
7. **Rank** and return top 3 with reasons

## Important Notes

- **Suitability scores are NOT catch probability** - they represent rules-based compatibility
- **Legal status requires runtime verification** - regulations change
- **Forecasts are decision support only** - verify with official sources
- **Safety warnings override recommendations** - prioritize safety

## Testing

```bash
# API tests
cd apps/api
pytest

# Web tests
cd apps/web
npm run test
npm run test:e2e
```

## Configuration

See `.env.example` for all configuration options.

Key settings:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection (optional)
- `OPEN_METEO_BASE_URL`: Forecast API endpoint

## Documentation

- [Traceability Matrix](docs/TRACEABILITY_MATRIX.md)
- [API Documentation](http://localhost:8000/docs)
- [OpenAPI Schema](packages/openapi/)

## License

Proprietary - All rights reserved.

## Acknowledgments

- Open-Meteo for marine forecast data
- Israel Meteorological Service for official verification
