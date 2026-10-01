# Requirement Traceability Matrix

This document maps requirements from the specification to their implementation and tests.

## Product Requirements (PRD)

| Requirement | Implementation | Tests |
|-------------|----------------|-------|
| Guided wizard mode | `apps/web/src/app/wizard/page.tsx` | Playwright tests |
| Natural-language chat | LLM adapter (optional) | - |
| Quick mode | `apps/web/src/app/quick/page.tsx` | Playwright tests |
| Expert mode | Result page with rule details | Playwright tests |
| Hebrew RTL UI | `apps/web/src/app/layout.tsx`, globals.css | Visual tests |
| Mobile-first responsive | Tailwind responsive classes | Playwright viewport tests |

## Engine Requirements

| Requirement | Implementation | Tests |
|-------------|----------------|-------|
| Normalize inputs | `src/engine/normalizer.py` | `test_normalizer.py` |
| Derive sea state | `Normalizer._derive_sea_state()` | `TestSeaState` |
| Create candidates | `src/engine/candidate_generator.py` | `test_candidate_generator.py` |
| Apply soft rules | `RuleEvaluator.evaluate_all()` | `TestSoftRules` |
| Apply hard exclusions | `RuleEvaluator.evaluate_all()` | `TestHardExclusions` |
| Choose compatible weight | `EquipmentValidator._select_weight()` | `TestWeightSelection` |
| Top 3 with rule IDs | `RuleEvaluator.rank_candidates()` | `TestRanking` |
| Expose versions | `RecommendationResponse.rules_version` | `test_scenarios.py` |
| Never call score probability | Schema documentation | Code review |

## Forecast Requirements

| Requirement | Implementation | Tests |
|-------------|----------------|-------|
| Open-Meteo integration | `src/services/forecast.py` | `test_forecast.py` |
| Cache requests | `ForecastCache` class | `test_forecast.py` |
| Provider metadata | `ForecastResponse.provider` | Schema validation |
| Handle failures | `ForecastError` exception | `test_forecast.py` |
| Editable fields | Request conditions override | `test_normalizer.py` |
| IMS verification link | `ForecastResponse.ims_verification_url` | Schema validation |

## API Requirements

| Requirement | Implementation | Tests |
|-------------|----------------|-------|
| POST /recommendations | `routers/recommendations.py` | `test_api.py` |
| GET /catalog/fish | `routers/catalog.py` | `test_api.py` |
| GET /catalog/lures | `routers/catalog.py` | `test_api.py` |
| GET /forecast | `routers/forecast.py` | `test_api.py` |
| POST /feedback | `routers/feedback.py` | `test_api.py` |
| Admin CRUD | `routers/admin.py` | `test_admin.py` |
| OpenAPI export | FastAPI auto-generation | CI build |

## Admin Requirements

| Requirement | Implementation | Tests |
|-------------|----------------|-------|
| Draft/validate/publish | `RuleStatus` enum, admin routes | `test_admin.py` |
| JSON import/export | `/admin/rules/export`, `/import` | `test_admin.py` |
| Change history | `RuleVersion` model | `test_admin.py` |
| Rollback | `/admin/rules/{id}/rollback` | `test_admin.py` |

## Quality Requirements

| Requirement | Implementation | Tests |
|-------------|----------------|-------|
| 60 seed scenarios | `test_scenarios.py` | `TestSeedScenarios` |
| Unit tests | `tests/test_*.py` | pytest |
| Integration tests | `tests/test_api.py` | pytest |
| Playwright tests | `apps/web/tests/` | Playwright |
| Property-based tests | `test_properties.py` | hypothesis |
| Determinism | `TestDeterminism` | pytest |
| No weight above max | `TestWeightConstraints` | pytest |

## Security Requirements

| Requirement | Implementation | Tests |
|-------------|----------------|-------|
| Anonymous default | No auth required for recommendations | - |
| Location rounding | Analytics config | - |
| Secrets separation | `.env.example`, no client secrets | Code review |
| Input validation | Pydantic schemas | Schema tests |
| Rate limiting | Middleware (TODO) | - |
| Admin auth | JWT authentication | `test_auth.py` |
| Audit trail | `RecommendationAudit` model | `test_audit.py` |

## Non-Functional Requirements

| Requirement | Implementation | Tests |
|-------------|----------------|-------|
| p95 < 600ms | Async implementation | Load tests |
| Graceful fallback | Forecast error handling | `test_forecast.py` |
| Cache external requests | `ForecastCache` | `test_forecast.py` |
| No client secrets | Environment variables | Code review |
| Accessible controls | Semantic HTML, ARIA | Accessibility audit |

## Files Mapping

### Schemas
- `recommendation_request.schema.json` → `src/schemas/recommendation.py`
- `recommendation_response.schema.json` → `src/schemas/recommendation.py`

### Knowledge
- `fish.json` → `src/services/knowledge.py`
- `lures.json` → `src/services/knowledge.py`
- `rules.json` → `src/services/knowledge.py`
- `colors.json` → `src/services/knowledge.py`
- `retrieves.json` → `src/services/knowledge.py`
- `locations_seed.json` → `src/services/knowledge.py`
- `equipment.json` → `src/services/knowledge.py`
- `sea_condition_matrix.json` → `src/services/knowledge.py`

### Documentation
- `PRODUCT_REQUIREMENTS.md` → This matrix
- `ARCHITECTURE.md` → Implementation structure
- `DECISION_ENGINE.md` → `src/engine/`
- `API_SPECIFICATION.md` → `src/routers/`
- `UI_UX.md` → `apps/web/`
- `LEGAL_SAFETY_COPY_HE.md` → UI warnings, response warnings
