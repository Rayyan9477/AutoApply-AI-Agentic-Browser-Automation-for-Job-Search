# AutoApply AI | Smart Job Application Assistant

<p align="center">
  <img src="https://img.shields.io/badge/backend-FastAPI-0f766e" alt="FastAPI">
  <img src="https://img.shields.io/badge/frontend-React%20%2B%20Vite-2563eb" alt="React and Vite">
  <img src="https://img.shields.io/badge/python-3.11+-1d4ed8" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/status-v2.0-f59e0b" alt="v2.0">
</p>

AutoApply AI is a full-stack platform that automates and manages the modern job application workflow: discover opportunities, tailor resumes, track applications, review analytics, and orchestrate browser-based automation from a single workspace.

## What It Does

- **Job Discovery** across LinkedIn, Indeed, Glassdoor, and Exa AI semantic search
- **ATS Resume Scoring** with multi-factor analysis (skills, keywords, experience, education)
- **Resume Tailoring** with LLM-powered content optimization and PDF/DOCX generation
- **Application Tracking** with status lifecycle, approval workflows, and batch processing
- **Browser Automation** via browser-use + Playwright for platform-specific job submissions
- **Real-time Dashboard** with funnel analytics, ATS score distribution, and LLM usage tracking

## Architecture

```
Frontend (React 18 + Vite + TypeScript)
  |
  REST API + WebSocket
  |
Backend (FastAPI)
  |- API Layer (/api/v1) -- jobs, applications, resumes, analytics, settings
  |- Service Layer -- orchestration and business logic
  |- Core Modules -- ATS scoring, browser automation, document engine, LLM client
  |- Workers -- Redis-backed async application processing
  '- Data Layer -- SQLite/PostgreSQL, Redis, FAISS vector indices
```

- **Backend:** FastAPI, SQLAlchemy 2.0 async, Pydantic v2, Redis, structlog, Prometheus
- **Frontend:** React 18, TypeScript, Vite — custom design-token UI (CSS variables + inline styles, no component library), TanStack Query, Zustand, Recharts
- **Automation:** browser-use + Playwright for platform workflows
- **AI:** AWS Bedrock via LiteLLM (default `bedrock/us.anthropic.claude-sonnet-4-6`), with the Bedrock Mantle OpenAI-compatible endpoint for the wider catalog and fallbacks; per-user BYO keys (OpenAI, Groq, Gemini, OpenRouter) remain an alternative
- **Data:** SQLite (default) or PostgreSQL, Redis queue/cache, FAISS vector indices

For a full breakdown, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Quick Start

### Docker Compose (recommended)

```bash
cp .env.example .env         # Configure at least one LLM provider
docker compose up --build
```

Development mode with hot reload:

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

#### Worker (separate terminal)

```bash
cd backend
arq app.workers.tasks.WorkerSettings
```

### Default Services

| Service | URL |
|---|---|
| Frontend | `http://localhost:3000` |
| Backend API | `http://localhost:8000` |
| API Docs (Swagger) | `http://localhost:8000/docs` |
| Health Check | `http://localhost:8000/health` |
| Prometheus Metrics | `http://localhost:8000/metrics` |
| Redis | `localhost:6379` |

## Configuration

Copy `.env.example` to `.env`. The platform LLM is AWS Bedrock, authenticated via the standard
AWS credential chain (env vars, `~/.aws`, or an instance role) — no API key is stored per user.
Per-user BYO keys (OpenAI, Groq, Gemini, OpenRouter — entered in Settings, encrypted at rest)
remain a supported alternative.

```env
# Database
DATABASE_URL=sqlite+aiosqlite:///data/db/autoapply.db
REDIS_URL=redis://localhost:6379/0

# LLM — AWS Bedrock (recommended)
LLM__PREFERRED_PROVIDER=bedrock
LLM__DEFAULT_MODEL=bedrock/us.anthropic.claude-sonnet-4-6
LLM__BEDROCK_REGION=us-east-1
# Bedrock Mantle — OpenAI-compatible Bedrock endpoint (bearer token self-generated from AWS creds)
LLM__MANTLE_API_BASE=https://bedrock-mantle.us-east-1.api.aws/v1
LLM__FALLBACK_PROVIDERS=["mantle/openai.gpt-oss-120b","bedrock/google.gemma-3-27b-it"]
AWS_ACCESS_KEY_ID=            # or leave blank to use ~/.aws / an instance role
AWS_SECRET_ACCESS_KEY=

# Application
APPLY_MODE=review              # autonomous | review | batch
MIN_ATS_SCORE=0.75
ENVIRONMENT=development

# Browser Automation
BROWSER__HEADLESS=true
BROWSER__MAX_PARALLEL=3
```

### Apply Modes

| Mode | Behavior |
|---|---|
| `review` | Applications created as `pending_review`; user approves before submission |
| `autonomous` | Applications enqueued immediately for automated submission |
| `batch` | Applications queued in bulk; user reviews and approves the batch |

## API Surface

All routes are under `/api/v1` (auth routes are public; everything else requires a JWT):

```
POST   /api/v1/auth/register             # Create account
POST   /api/v1/auth/login                # OAuth2 password login -> access token
POST   /api/v1/auth/refresh              # Rotate refresh token (httpOnly cookie)
POST   /api/v1/auth/logout               # Revoke session
POST   /api/v1/auth/forgot-password      # Request password-reset email
POST   /api/v1/auth/reset-password       # Redeem reset token, set new password
GET    /api/v1/auth/me                   # Current user
GET    /api/v1/auth/ws-ticket            # Short-lived WebSocket ticket
DELETE /api/v1/auth/account              # Soft-delete account

POST   /api/v1/jobs/search               # Multi-platform job search
GET    /api/v1/jobs                      # List jobs (paginated)
GET    /api/v1/jobs/{id}                 # Get job details
POST   /api/v1/jobs/{id}/analyze         # ATS match analysis
DELETE /api/v1/jobs/{id}                 # Delete job

POST   /api/v1/applications              # Create application
POST   /api/v1/applications/batch        # Batch create
GET    /api/v1/applications              # List applications
GET    /api/v1/applications/{id}         # Get application detail
PUT    /api/v1/applications/{id}/approve  # Approve for submission
POST   /api/v1/applications/bulk-approve  # Approve many at once
PUT    /api/v1/applications/{id}/status   # Update status
POST   /api/v1/applications/{id}/cover-letter  # Generate cover letter
POST   /api/v1/applications/{id}/intervention  # Answer CAPTCHA/2FA prompt

POST   /api/v1/resumes/upload            # Upload resume (PDF/DOCX)
GET    /api/v1/resumes                   # List resumes
POST   /api/v1/resumes/generate          # Generate tailored resume
POST   /api/v1/resumes/{id}/score        # ATS score against job
POST   /api/v1/resumes/{id}/optimize     # ATS-optimize a resume
GET    /api/v1/resumes/{id}/download     # Download as PDF or DOCX

GET    /api/v1/analytics/dashboard       # Dashboard stats
GET    /api/v1/analytics/funnel          # Application funnel
GET    /api/v1/analytics/ats-scores      # Score distribution
GET    /api/v1/analytics/llm-usage       # Token and cost tracking
GET    /api/v1/analytics/timeline        # Daily activity timeline

GET    /api/v1/settings                  # Get settings
PUT    /api/v1/settings                  # Update settings
GET    /api/v1/settings/llm-providers    # Provider status

POST   /api/v1/platform-sessions         # Import a captured platform session (encrypted)
GET    /api/v1/platform-sessions         # List connected platforms (no cookies returned)
DELETE /api/v1/platform-sessions/{platform}  # Disconnect a platform

GET    /api/v1/admin/system-issues       # Harness-detected issues (superuser only)

WS     /ws?ticket=...                    # Real-time event stream (ticket-authenticated)
GET    /health                           # Health check (real readiness probe)
```

## Repository Layout

```
backend/app/
  api/            # FastAPI routes (v1) + WebSocket
  core/           # ATS, automation, documents, LLM, matching, job discovery
  services/       # Business logic orchestration
  models/         # SQLAlchemy models (Job, Application, Resume, LLMUsage, UserSettings)
  schemas/        # Pydantic request/response schemas
  db/             # Database session + Redis + Alembic migrations
  workers/        # Arq background workers (tasks.py)
  observability/  # Structlog + Prometheus metrics

frontend/src/
  components/     # Reusable UI (layout, jobs, applications, resumes, dashboard, common)
  pages/          # Route-level pages (Dashboard, Jobs, Applications, Resumes, Settings, Analytics)
  hooks/          # React hooks (useJobs, useApplications, useResumes, useWebSocket, etc.)
  services/       # API client layer (Axios)
  store/          # Zustand state management
  types/          # TypeScript type definitions

templates/        # Resume and cover letter HTML/CSS templates
data/             # Runtime data (gitignored): db, uploads, sessions, vector indices, logs
docker/           # Dockerfiles + nginx config
docs/             # Setup breadcrumbs, bug log, design prompt
deploy/           # Production runbook, credentials checklist, bootstrap script
```

## Development Commands

```bash
# Backend
cd backend
pytest tests/ -v                    # Run tests
ruff check app/                     # Lint
ruff format app/                    # Format

# Frontend
cd frontend
npm run lint                        # Lint
npm run build                       # Production build
```

## Current Status

### Shipped

- Multi-tenant auth: register/login with JWT access + rotating refresh tokens, and a full
  password-reset flow (forgot + reset screens, pluggable log/smtp mailer)
- Job search across platforms + Exa semantic search, with ATS match analysis per job
- Resume upload/parse, tailored generation, ATS scoring, and one-click optimization
- Applications pipeline: create/batch, review/approve (incl. bulk approve), cover-letter
  generation, CAPTCHA/2FA intervention endpoint, and live status over WebSocket
- Analytics (dashboard stats, funnel, ATS distribution, LLM usage, timeline)
- Admin system-health view backed by the self-evolving harness (superuser only)
- Platform session-import API (`/api/v1/platform-sessions`) — per-user, encrypted at rest
- Arq worker + Redis pub/sub event bus; AWS Bedrock LLM with fallback chain
- 660+ backend tests and 133 frontend tests

### In Progress

- Live browser-based application submission is gated behind `BROWSER__LIVE_APPLY=false`
  awaiting the real-browser (headful) spike: assisted-login capture UX, anti-bot posture,
  and platform flow validation on a headful browser host

## Responsible Use

This project touches hiring workflows, personal data, and platform automation.

- Review all AI-generated materials before submission
- Respect platform terms, rate limits, and automation policies
- Do not misrepresent qualifications or fabricate experience
- Protect stored credentials and personal profile data
- Keep human approval in the loop unless you have a strong reason not to

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) -- system architecture and data flows
- [docs/SETUP_AND_BREADCRUMBS.md](docs/SETUP_AND_BREADCRUMBS.md) -- current operational reality and setup checklist
- [deploy/RUNBOOK.md](deploy/RUNBOOK.md) -- production deployment runbook

## Adding a New Platform

1. Create `backend/app/core/automation/platforms/{name}.py`
2. Implement the `JobPlatform` ABC (`login`, `search`, `scrape_details`, `apply`)
3. Register in `platforms/__init__.py`

## Adding a Resume Template

1. Create `templates/resume/{name}/template.html` + `style.css`
2. Add the template name to `RESUME_TEMPLATES` in `backend/app/config/constants.py`
