# AutoApply AI — Project Conventions

## Quick Start
```bash
docker compose up --build        # Start all services
docker compose -f docker-compose.yml -f docker-compose.dev.yml up  # Dev mode with hot reload
```

## Architecture
- Backend: FastAPI (Python 3.11) at `backend/app/`
- Frontend: React + MUI + TypeScript at `frontend/src/`
- Queue: Redis for async job processing
- Database: SQLite (default), PostgreSQL optional

## Directory Layout
- `backend/app/config/` — Settings and constants
- `backend/app/core/` — Domain modules (ats/, automation/, documents/, llm/, matching/)
- `backend/app/api/v1/` — FastAPI routes
- `backend/app/services/` — Business logic layer
- `backend/app/models/` — SQLAlchemy models
- `backend/app/schemas/` — Pydantic request/response schemas
- `backend/app/workers/` — Background queue workers
- `frontend/src/` — React SPA

## Coding Standards
- Python: async-first, structlog, Pydantic v2, SQLAlchemy 2.0 Mapped[] annotations
- TypeScript: strict mode, no `any`, React Query for server state, Zustand for UI state
- Max 300 lines per file
- Naming: snake_case (Python), PascalCase components / camelCase hooks (TypeScript)

## Adding a New Platform
1. Create `backend/app/core/automation/platforms/{name}.py`
2. Implement `JobPlatform` ABC (login, search, scrape_details, apply)
3. Register in `platforms/__init__.py`: `platform_registry.register("name", NamePlatform)`

## Adding a Resume Template
1. Create `templates/resume/{name}/template.html` + `style.css`
2. Add template name to `RESUME_TEMPLATES` in `backend/app/config/constants.py`

## Common Commands
```bash
# Backend
cd backend && uvicorn app.main:app --reload
pytest tests/ -v
ruff check app/
ruff format app/

# Frontend
cd frontend && npm run dev
npm run build
npm run lint
```
