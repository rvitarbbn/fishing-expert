# OpenAPI Specification

This package contains the exported OpenAPI 3.1 schema for the Mediterranean Shore Fishing Expert API.

## Generating the Schema

Run the following command from the `apps/api` directory:

```bash
python -c "from src.main import app; import json; print(json.dumps(app.openapi(), indent=2))" > ../../packages/openapi/openapi.json
```

Or use the provided script:

```bash
./scripts/export-openapi.sh
```

## Using the Schema

The `openapi.json` file can be used with:

- **ChatGPT Actions**: Import as a GPT action schema
- **Claude Projects**: Reference for API integration
- **API Documentation**: Generate docs with Swagger UI or Redoc
- **Client Generation**: Generate typed clients for various languages

## Endpoints

### Recommendations
- `POST /api/v1/recommendations` - Generate lure recommendations
- `GET /api/v1/recommendations/{id}` - Retrieve a recommendation

### Catalog
- `GET /api/v1/catalog/fish` - List target fish species
- `GET /api/v1/catalog/lures` - List lure types
- `GET /api/v1/catalog/retrieves` - List retrieve methods
- `GET /api/v1/catalog/colors` - List color families
- `GET /api/v1/catalog/locations` - List seed locations

### Forecast
- `GET /api/v1/forecast` - Get marine/weather forecast

### Feedback
- `POST /api/v1/recommendations/{id}/feedback` - Submit feedback

### Admin
- `GET /api/v1/admin/rules` - List rules
- `POST /api/v1/admin/rules` - Create rule
- `PUT /api/v1/admin/rules/{id}` - Update rule
- `POST /api/v1/admin/rules/{id}/validate` - Validate rule
- `POST /api/v1/admin/rules/{id}/publish` - Publish rule
- `POST /api/v1/admin/rules/{id}/rollback` - Rollback rule
- `GET /api/v1/admin/rules/export` - Export rules
- `POST /api/v1/admin/rules/import` - Import rules
