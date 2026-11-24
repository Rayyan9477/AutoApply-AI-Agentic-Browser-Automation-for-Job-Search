# AutoApply AI | Smart Job Application Assistant

<p align="center">
  <img src="https://img.shields.io/badge/backend-FastAPI-0f766e" alt="FastAPI">
  <img src="https://img.shields.io/badge/frontend-React%2018%20%2B%20Vite-2563eb" alt="React 18 and Vite">
  <img src="https://img.shields.io/badge/python-3.11+-1d4ed8" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/database-Neon%20Postgres%20%7C%20SQLite-00e599" alt="Database">
  <img src="https://img.shields.io/badge/ai-AWS%20Bedrock%20%2B%20Mantle-ff9900" alt="AWS Bedrock">
  <img src="https://img.shields.io/badge/status-Enterprise%20MVP-f59e0b" alt="Enterprise MVP">
</p>

AutoApply AI is an enterprise-grade, multi-tenant agentic platform that automates and manages the modern job search lifecycle: discover opportunities, match and tailor resumes, track application funnels, execute browser-based submissions, and continuously self-heal using an LLM evaluation harness.

## What It Does

- **Multi-Platform Job Discovery:** Ingest opportunities from LinkedIn, Indeed, Glassdoor, and Exa AI semantic search with automatic deduplication. Platform board searches execute asynchronously via Arq background workers with real-time WebSocket progress chips and an inline heartbeat fallback if the worker is offline.
- **ATS Resume Scoring:** Multi-factor algorithmic evaluation combining cosine TF-IDF keyword overlap, experience depth, and educational alignment.
- **Dynamic Resume & Cover Letter Tailoring:** LLM-powered tailoring targeting specific job descriptions, generating clean HTML, PDF, and DOCX outputs from modular templates. Full cover letter generation and authenticated download.
- **Application Pipeline Management:** State tracking (`pending_review`/`queued` → `approved` → `applying` → `applied` → `interview` → `offer`/`rejected`, plus terminal `withdrawn`, `failed` and `simulated`) behind an enforced manual-transition state machine, with single, bulk, and automated approval workflows, and list pagination. With `BROWSER__LIVE_APPLY` off (the default) a run ends as `simulated` and is never counted as applied.
- **Agentic Browser Automation:** Headful/headless browser execution using `browser-use` and Playwright for platform-specific form navigation and document upload.
- **Human-in-the-Loop Interventions:** the apply agent's `request_human_help` tool publishes an intervention event and blocks on a Redis `BLPOP`/`RPUSH` rendezvous while the user resolves a CAPTCHA/2FA prompt in the WebSocket-driven modal. Tool-wired and unit-tested, not yet exercised against a live browser.
- **Self-Evolving Evaluation Harness:** Autonomous post-run LLM Judge (`RunVerdict`), rule-based diagnostic engine (`RunDiagnosis`), PII-scrubbed per-user skill distillation (`DomainSkill`), and rolling 6-hour anomaly detection (`SystemIssue`).
- **Fail-Closed Multi-Tenancy & Security:** Argon2id password hashing, rotating refresh token families, fail-closed row-level tenant filtering (`TenantMixin` + `TenantScopeError`), per-user domain skills, and envelope encryption for platform sessions and credentials. GDPR account deletion with 30-day grace period.
- **Per-User LLM Monthly Budget:** Enforced monthly spend cap in USD (`LLM__USER_MONTHLY_BUDGET_USD`, default $5.0) evaluated in UTC calendar months. Exceeding budget returns HTTP 402 Payment Required and marks worker jobs as failed.
- **Cross-Dialect Naive-UTC Storage:** All model timestamps use a custom `UTCDateTime` TypeDecorator storing naive UTC datetimes consistently on both SQLite and PostgreSQL.
- **Isolated Document Storage:** Unified asynchronous storage abstraction supporting local filesystem and S3/Cloudflare R2 with strict per-tenant folder boundaries. Uses `pypdf` for fast text extraction.
- **Real-Time Funnel Analytics:** Live dashboard featuring application conversion funnels, ATS score distributions, token usage, real-time activity streams over WebSockets, and monthly budget progress.

## Architecture

```
Frontend (React 18 + Vite + TypeScript)
  |  Custom Design Tokens (CSS Variables) + TanStack Query + Zustand
  |
  +-- REST API (JWT Bearer Auth) --------------------------------+
  |                                                              |
  +-- WebSocket (/ws?ticket=...) <----------------------------+  |
                                                              |  |
Backend (FastAPI + Async SQLAlchemy 2.0)                      |  |
  |- API Layer (/api/v1) -- Auth, Jobs, Resumes, Applications |  |
  |- Ambient Multi-Tenancy (TenantMixin + do_orm_execute)     |  |
  |- Service Layer -- Orchestration, ATS scoring, Tailoring   |  |
  |- Storage Layer -- Isolated Local / Cloudflare R2 / S3     |  |
  |- Secrets Layer -- Envelope encryption (Fernet / KMS)      |  |
  |- Harness Layer -- LLM Judge, Failure Diagnosis, Skills    |  |
  |                                                           |  |
  v Enqueue                                                   |  |
Redis Cluster                                                 |  |
  |- Arq Job Queue (run_apply, purge_deleted_accounts)        |  |
  |- Pub/Sub Event Bridge (ws:user:{id}) ---------------------+  |
  '- Intervention Rendezvous (intervene:{application_id})        |
                                                                 |
Workers (Arq Tasks + browser-use + Playwright)                   |
  |- Browser Session Controller                                  |
  |- Evaluation Harness Runner ----------------------------------+
  v
Platform LLM (AWS Bedrock: Claude Sonnet 4.6 / Gemma 3 / Bedrock Mantle)
```

- **Backend:** FastAPI, SQLAlchemy 2.0 async, Pydantic v2, Redis, structlog, Prometheus
- **Frontend:** React 18, TypeScript, Vite — custom design-token UI (CSS variables + inline styles, zero heavyweight UI library dependencies), TanStack Query, Zustand, Recharts
- **Automation:** browser-use + Playwright for platform workflows
- **AI Engine:** AWS Bedrock via LiteLLM (default `bedrock/us.anthropic.claude-sonnet-4-6`), Bedrock Mantle OpenAI-compatible endpoint, and Gemma 3 (`bedrock/google.gemma-3-27b-it`) fallback chain. Everyone runs on the platform Bedrock credentials: the backend can resolve a per-user BYO key (`build_llm_client_for_user`), but no API endpoint stores one yet
- **Persistence:** Neon PostgreSQL (production, Alembic migrated) or SQLite (local development), Redis queue/cache, FAISS vector indices

For a detailed breakdown, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Quick Start

### Docker Compose (Recommended)

```bash
cp .env.example .env         # Configure AWS Bedrock or LLM keys
docker compose up --build
```

Development mode with hot reloading:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

### Local Development

#### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

#### Worker (Separate Terminal)

```bash
cd backend
arq app.workers.tasks.WorkerSettings
```

### Default Endpoints

| Service | URL | Notes |
|---|---|---|
| Frontend SPA | `http://localhost:3000` | Vite Dev Server |
| Backend API | `http://localhost:8000` | FastAPI Root |
| API Interactive Docs | `http://localhost:8000/docs` | OpenAPI / Swagger UI |
| Health Check | `http://localhost:8000/health` | Readiness probe (DB + Redis check) |
| Prometheus Metrics | `http://localhost:8000/metrics` | Bearer token authenticated |
| Redis Server | `localhost:6379` | Queue, Pub/Sub, Rendezvous |

## Configuration

Copy `.env.example` to `.env`. The default platform LLM is AWS Bedrock, authenticated via the standard AWS credential chain (environment variables, `~/.aws`, or an IAM instance role) — no API key is stored per user.

The frontend SPA communicates with the backend via `VITE_API_BASE_URL` (defaults to `/api/v1` through the local Vite proxy, or set e.g. `http://localhost:8000/api/v1`).

```env
# Database
DATABASE_URL=sqlite+aiosqlite:///data/db/autoapply.db
# DATABASE_URL=postgresql+asyncpg://user:pass@host/autoapply?ssl=require
REDIS_URL=redis://localhost:6379/0

# LLM — AWS Bedrock & Bedrock Mantle
LLM__PREFERRED_PROVIDER=bedrock
LLM__DEFAULT_MODEL=bedrock/us.anthropic.claude-sonnet-4-6
LLM__BEDROCK_REGION=us-east-1
LLM__MANTLE_API_BASE=https://bedrock-mantle.us-east-1.api.aws/v1
LLM__FALLBACK_PROVIDERS=["mantle/openai.gpt-oss-120b","bedrock/google.gemma-3-27b-it"]
LLM__USER_MONTHLY_BUDGET_USD=5.0 # Monthly spend cap in USD (calendar month UTC; <=0 disables)
AWS_ACCESS_KEY_ID=            # or leave blank to use ~/.aws / instance role
AWS_SECRET_ACCESS_KEY=

# Storage & Encryption
STORAGE__PROVIDER=local       # 'local' or 's3' (Cloudflare R2 / AWS S3)
SECRETS__PROVIDER=local       # 'local' (Fernet) or 'aws_kms'
SECRETS__APP_KEYS=            # Comma-separated Fernet keys for local provider

# Application Policy
APPLY_MODE=review              # autonomous | review | batch
# ATS threshold is configured per-user (UserSettings.min_ats_score)
ENVIRONMENT=development

# Browser Automation
BROWSER__HEADLESS=true
BROWSER__MAX_PARALLEL=3
BROWSER__LIVE_APPLY=false     # Toggle for live automated submissions
```

### Apply Modes

| Mode | Behavior |
|---|---|
| `review` | Applications are created as `pending_review`; user approves before submission |
| `autonomous` | Applications are enqueued immediately for automated submission |
| `batch` | Applications are queued in bulk; user reviews and approves the batch |

## API Surface

All routes are mounted under `/api/v1` (authentication routes are public; other endpoints require JWT Bearer authorization):

### Authentication & Sessions
```http
POST   /api/v1/auth/register             # Create account
POST   /api/v1/auth/login                # OAuth2 password login -> access token + httpOnly refresh cookie
POST   /api/v1/auth/refresh              # Rotate refresh token family
POST   /api/v1/auth/logout               # Revoke current refresh token family
POST   /api/v1/auth/forgot-password      # Request password-reset link (no account enumeration)
POST   /api/v1/auth/reset-password       # Redeem single-use token, set new password
GET    /api/v1/auth/me                   # Get authenticated user profile
GET    /api/v1/auth/ws-ticket            # Generate short-lived ticket for WebSocket auth
DELETE /api/v1/auth/account              # Soft-delete account (30-day grace, permanent worker purge; typed confirm, no restore)
```

### Jobs & Discovery
```http
POST   /api/v1/jobs/search               # Search Exa (sync) + enqueue boards (async Arq)
GET    /api/v1/jobs/search/{search_id}   # Poll status and board progress of background discovery
GET    /api/v1/jobs                      # List discovered jobs (paginated with Pager, filtered)
GET    /api/v1/jobs/{id}                 # Get job details and analysis
POST   /api/v1/jobs/{id}/analyze         # Trigger ATS match analysis against user resume
DELETE /api/v1/jobs/{id}                 # Delete job record
```

### Application Pipeline
```http
POST   /api/v1/applications              # Create application for job
POST   /api/v1/applications/batch        # Batch create applications
GET    /api/v1/applications              # List applications (paginated with Pager, filterable)
GET    /api/v1/applications/{id}         # Get application details with timeline
PUT    /api/v1/applications/{id}/approve  # Approve application for submission
POST   /api/v1/applications/bulk-approve  # Bulk approve pending applications
PUT    /api/v1/applications/{id}/status   # Manually update lifecycle status
POST   /api/v1/applications/{id}/cover-letter  # Generate tailored cover letter
GET    /api/v1/applications/{id}/cover-letter/download # Download cover letter (PDF/DOCX)
POST   /api/v1/applications/{id}/intervention  # Submit response to CAPTCHA/2FA prompt
DELETE /api/v1/applications/{id}         # Delete application record
```

### Resumes & Documents
```http
POST   /api/v1/resumes/upload            # Upload resume file (PDF, DOCX via pypdf)
GET    /api/v1/resumes                   # List uploaded/tailored resumes
GET    /api/v1/resumes/{id}              # Get resume metadata and parsed structure
GET    /api/v1/resumes/{id}/profile-data # Extracted structured profile data
POST   /api/v1/resumes/generate          # Generate tailored resume for job
POST   /api/v1/resumes/{id}/score        # Calculate ATS score breakdown
POST   /api/v1/resumes/{id}/optimize     # Optimize content for target keywords
GET    /api/v1/resumes/{id}/download     # Download formatted PDF or DOCX
DELETE /api/v1/resumes/{id}              # Delete resume record
```

### Analytics & Reporting
```http
GET    /api/v1/analytics/dashboard       # High-level aggregate metrics
GET    /api/v1/analytics/funnel          # Lifecycle stage conversion funnel
GET    /api/v1/analytics/ats-scores      # ATS match score histogram
GET    /api/v1/analytics/llm-usage       # Token usage and estimated cost tracking
GET    /api/v1/analytics/llm-budget      # Monthly LLM budget limit, spend, remaining, reset date
GET    /api/v1/analytics/timeline        # Daily activity and submission timeline
```

### User Settings & Preferences
```http
GET    /api/v1/settings                  # Retrieve user preferences
PUT    /api/v1/settings                  # Update preferences (apply mode, min score)
GET    /api/v1/settings/llm-providers    # Provider availability and active defaults
```

### Platform Sessions (Assisted Login)
```http
POST   /api/v1/platform-sessions         # Store encrypted browser storage state
GET    /api/v1/platform-sessions         # List active connected platform sessions
DELETE /api/v1/platform-sessions/{platform}  # Disconnect and revoke session
```

### System Administration & Harness
```http
GET    /api/v1/admin/system-issues       # List detected harness issues (superuser)
POST   /api/v1/admin/system-issues/{id}/resolve  # Mark system issue resolved
```

### Real-Time & Monitoring
```http
WS     /ws?ticket=...                    # WebSocket live updates and intervention prompts
GET    /health                           # Real readiness probe (DB + Redis checks)
GET    /metrics                          # Prometheus metrics (Bearer token auth)
```

## Repository Layout

```
backend/app/
  api/            # FastAPI route definitions (v1) + WebSocket endpoint
  config/         # Pydantic BaseSettings, constants, and logging configuration
  core/           # Domain logic engines:
    ats/          # Multi-factor ATS scoring engine and keyword extraction
    automation/   # browser-use and Playwright automation drivers and platforms
    documents/    # PDF/DOCX parsing, Jinja2 rendering, WeasyPrint generation
    harness/      # Evaluation harness: LLM judge, diagnostic engine, skills, issues
    job_discovery/# Multi-platform scrapers (LinkedIn, Indeed, Glassdoor) + Exa AI
    llm/          # Bedrock, Mantle, and LiteLLM abstraction layer
    matching/     # Candidate-to-job matching algorithms and embeddings
    secrets/      # Key encryption providers (Fernet, KMS) and credential store
    storage/      # Storage abstraction layer (Local filesystem, Cloudflare R2 / S3)
  db/             # Session factories, Redis pool, base models, tenant filtering
  models/         # 13 SQLAlchemy models (User, UserSettings, UserCredential,
                  # PlatformSession, Job, Application, Resume, LLMUsage, AuditLog,
                  # RunVerdict, RunDiagnosis, DomainSkill, SystemIssue)
  schemas/        # Pydantic request and response schemas
  services/       # Business orchestration services
  workers/        # Arq background worker tasks and queue settings

frontend/src/
  components/     # Modular UI components (Layout, Jobs, Applications, Resumes, Common)
  hooks/          # Custom React hooks (useJobs, useApplications, useWebSocket, etc.)
  pages/          # Application views (Dashboard, Jobs, Applications, Resumes, Settings, etc.)
  services/       # Axios API client with automatic token refresh interceptor
  store/          # Zustand state stores (useAuthStore, useAppStore, useUiStore)
  styles/         # Design token CSS definitions (theme.css)
  types/          # TypeScript interface definitions

templates/        # HTML/CSS Jinja2 templates for resume and cover letter compilation
deploy/           # Production deployment runbook, credentials guide, bootstrap script
docs/             # Operational breadcrumbs, architectural notes, design decisions
docker/           # Production and development Docker configurations
```

## Development Commands

```bash
# Backend Testing & Code Quality
cd backend
pytest tests/ -q                    # Complete test suite (1295 passed, 3 skipped SQLite default)
# Opt-in full suite on PostgreSQL (1298 tests):
# AUTOAPPLY_TEST_DATABASE_URL=postgresql+asyncpg://postgres:t@localhost:55432/autoapply_test pytest tests/ -q -o asyncio_default_test_loop_scope=session
ruff check app tests scripts        # Lint Python codebase
ruff format app tests scripts       # Format Python codebase
mypy app                            # Static type validation (clean)

# Frontend Testing & Code Quality
cd frontend
npm test                            # Vitest component & hook suite (245 passed across 46 files)
npm run lint                        # ESLint validation
npm run build                       # Production Vite build
```

## Status & Roadmap

### Shipped (Enterprise MVP)
- Multi-tenant authentication with Argon2id hashing, rotating refresh token families, and secure password reset.
- Fail-closed row-level multi-tenancy isolation via SQLAlchemy event filters (`TenantMixin` + `TenantScopeError`).
- Per-user learned domain navigation skills (`DomainSkill` with `user_id` and CASCADE) preventing cross-tenant steering; legacy unowned rows wiped in migration 0008 (deploy note: back up `domain_skills` on live DB prior to upgrade).
- Per-user monthly LLM budget cap (`LLM__USER_MONTHLY_BUDGET_USD` default $5.0) returning HTTP 402 on breach and failing worker jobs gracefully.
- Asynchronous multi-platform job board discovery offloaded to background Arq tasks with live WebSocket progress chips and inline worker heartbeat fallback (`arq:queue:health-check`).
- Cover letter generation and authenticated download, pagination controls across applications and jobs (`Pager`), and GDPR account deletion with typed email confirmation.
- Cross-dialect naive-UTC datetime storage convention enforced by `UTCDateTime` TypeDecorator on both SQLite and PostgreSQL.
- End-to-end resume lifecycle: upload, structure parsing via `pypdf`, ATS multi-factor scoring with honest weighting, tailoring, and export.
- Full application management pipeline with single, batch, and automated workflows, backed by an enforced status state machine.
- AWS Bedrock and Bedrock Mantle enterprise LLM integration with automatic fallback chain.
- Human-in-the-Loop intervention rendezvous for CAPTCHA/2FA challenges (tool-wired in browser agent loop).
- Continuous learning evaluation harness: LLM judge, diagnostic engine, skill distillation, and rolling anomaly detection.
- Envelope-encrypted credential store for imported platform sessions (`storage_state.json`), with a Connected Platforms card in Settings to import, list and disconnect them; expired sessions fail fast.
- Apply target resolution: Exa/career-site jobs (Greenhouse, Lever, Workday, ...) are appliable without a saved session; LinkedIn/Indeed/Glassdoor still need one.
- Retry endpoint for `failed`/`simulated`/`withdrawn` applications and a cron reaper for rows stuck in `applying`/`approved`/`queued`.
- Tenant-isolated object storage supporting local disk and Cloudflare R2 / S3.
- Real-time Redis Pub/Sub WebSocket event stream with ticket-based authentication.
- Lean dependencies with version caps on `spacy<3.8` (PII false positive protection) and `litellm<1.81` (fallback pricing preservation).
- Over 1295 backend tests (3 skipped PG-only legs) and 245 frontend tests passing with zero lint warnings.

### In Progress
- **Real-Browser Validation Spike:** Live submission validation using `backend/scripts/spike_apply.py` on headful browser infrastructure.
- **Assisted Login Capture UX:** Interactive browser session capture (today a session is imported by pasting or uploading `storage_state.json`).
- **CI and deploy:** CI is red at the apt step (`libgdk-pixbuf2.0-0` was renamed `libgdk-pixbuf-2.0-0`), and images lack `alembic.ini`. See [MASTER_AUDIT_AND_COMPILATION_REPORT.md](MASTER_AUDIT_AND_COMPILATION_REPORT.md).

## Responsible Use

This software automates hiring workflows, handles sensitive personal data, and interacts with third-party web platforms.

- Always review AI-generated resumes and cover letters prior to final submission.
- Comply with all platform terms of service, rate limits, and automation policies.
- Safeguard your stored credentials, session tokens, and personal profile information.
- Maintain human-in-the-loop review mode unless you have fully validated your automation pipelines.

## Documentation Index

- [ARCHITECTURE.md](ARCHITECTURE.md) — Comprehensive technical architecture, data flows, and schema definitions.
- [docs/SETUP_AND_BREADCRUMBS.md](docs/SETUP_AND_BREADCRUMBS.md) — Operational setup checklist and engineering breadcrumbs.
- [deploy/RUNBOOK.md](deploy/RUNBOOK.md) — Production deployment runbook for cost-efficient cloud hosting.
- [deploy/CREDENTIALS.md](deploy/CREDENTIALS.md) — Production credentials and secret management guide.
