# AutoApply AI — Project Conventions

## Quick Start
```bash
docker compose up --build        # Start all services
docker compose -f docker-compose.yml -f docker-compose.dev.yml up  # Dev mode with hot reload
```

## Architecture
- **Backend:** FastAPI (Python 3.11), SQLAlchemy 2.0 async, Pydantic v2, Arq worker, Redis at `backend/app/`
- **Frontend:** React 18 + Vite + TypeScript (custom design-token UI using CSS variables in `frontend/src/styles/theme.css` + inline styles; zero external component libraries like Tailwind/MUI) at `frontend/src/`
- **AI Engine:** AWS Bedrock via LiteLLM (`bedrock/us.anthropic.claude-sonnet-4-6`), Bedrock Mantle OpenAI-compatible endpoint, and fallback chain (`bedrock/google.gemma-3-27b-it`)
- **Queue & Real-Time:** Redis for Arq worker jobs, WebSocket pub/sub event bus (`ws:user:{id}`), and CAPTCHA/2FA intervention rendezvous (`intervene:{application_id}`)
- **Database:** Neon PostgreSQL (production, migrated to head `0006`) or SQLite (dev/test)
- **Storage:** Pluggable async storage (`local` disk or `s3`/Cloudflare R2) with strict tenant prefixing
- **Security:** Argon2id password hashing, rotating refresh tokens with reuse revocation, envelope encryption for user keys and sessions (`CredentialStore` + Fernet/KMS)

## Directory Layout
- `backend/app/api/v1/` — FastAPI routes + WebSocket endpoint
- `backend/app/config/` — Settings (`BaseSettings`), constants, and logging configuration
- `backend/app/core/` — Domain engines:
  - `ats/` — Multi-factor ATS scoring and keyword extraction
  - `automation/` — browser-use & Playwright platform drivers
  - `documents/` — PDF/DOCX parsing and WeasyPrint rendering
  - `harness/` — Self-evolving evaluation harness (LLM judge, diagnosis, skills, issues)
  - `job_discovery/` — Scrapers (LinkedIn, Indeed, Glassdoor) + Exa AI search
  - `llm/` — Bedrock, Mantle, and LiteLLM abstraction client
  - `matching/` — Job-candidate matching algorithms and embeddings
  - `secrets/` — Envelope encryption providers (Fernet, KMS) and credential store
  - `storage/` — Isolated storage engine (Local disk, S3 / Cloudflare R2)
- `backend/app/db/` — Sessions, Redis pool, and ambient `do_orm_execute` tenant filtering
- `backend/app/models/` — 13 SQLAlchemy models (`TenantMixin` for row-level isolation)
- `backend/app/schemas/` — Pydantic request/response schemas
- `backend/app/services/` — Business logic orchestration
- `backend/app/workers/` — Arq background workers (`tasks.py`)
- `frontend/src/` — React SPA:
  - `components/` — Modular UI components (Layout, Jobs, Applications, Resumes, Common)
  - `hooks/` — React hooks (useJobs, useApplications, useWebSocket, etc.)
  - `pages/` — Application views (Dashboard, Jobs, Applications, Resumes, Settings, etc.)
  - `services/` — Axios client with token refresh interceptor
  - `store/` — Zustand stores (`useAuthStore`, `useAppStore`, `useUiStore`)
  - `styles/` — Design token system (`theme.css`)

## Coding Standards
- **Python:** async-first, structlog, Pydantic v2, SQLAlchemy 2.0 `Mapped[]` annotations.
  - Multi-tenancy: All tenant-scoped models inherit `TenantMixin` and queries must use `get_tenant_db`.
  - Credentials: Never log or store raw secrets; always use `CredentialStore`.
- **TypeScript:** strict mode, zero `any`, TanStack Query for server state caching, Zustand for UI state.
  - Design Tokens: Use `var(--...)` tokens defined in `theme.css`. Do NOT install or introduce external component libraries.
- **File Length:** Target max 300 lines per file.
- **Naming:** snake_case (Python), PascalCase components / camelCase hooks (TypeScript).

## Adding a New Platform
1. Create `backend/app/core/automation/platforms/{name}.py`
2. Implement `JobPlatform` ABC (`login`, `search`, `scrape_details`, `apply`)
3. Register in `platforms/__init__.py`: `platform_registry.register("name", NamePlatform)`

## Adding a Resume Template
1. Create `templates/resume/{name}/template.html` + `style.css`
2. Add template name to `RESUME_TEMPLATES` in `backend/app/config/constants.py`

## Common Commands
```bash
# Backend
cd backend && uvicorn app.main:app --reload
pytest tests/ -v                    # Run all tests
ruff check app/                     # Lint Python
ruff format app/                    # Format Python
mypy app/                           # Static type validation

# Frontend
cd frontend && npm run dev          # Dev server
npm test                            # Run Vitest suite
npm run lint                        # Lint TypeScript/React
npm run build                       # Production build
```

