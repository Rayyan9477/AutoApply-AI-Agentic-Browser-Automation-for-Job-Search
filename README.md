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
Frontend (React + MUI + Vite)
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
- **Frontend:** React 18, TypeScript, Vite, MUI, TanStack Query, Zustand, Recharts
- **Automation:** browser-use + Playwright for platform workflows
- **AI:** LiteLLM + Portkey gateway with OpenAI, Groq, Gemini, OpenRouter support
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
python -m app.workers.application_worker
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

Copy `.env.example` to `.env` and set at least one LLM provider key:

```env
# Database
DATABASE_URL=sqlite+aiosqlite:///data/db/autoapply.db
REDIS_URL=redis://localhost:6379/0

# LLM (set at least one)
LLM__PREFERRED_PROVIDER=openai
LLM__DEFAULT_MODEL=gpt-4o
LLM__OPENAI_API_KEY=
LLM__GROQ_API_KEY=
LLM__OPENROUTER_API_KEY=
LLM__GEMINI_API_KEY=

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

All routes are under `/api/v1`:

```
POST   /api/v1/jobs/search              # Multi-platform job search
GET    /api/v1/jobs                      # List jobs (paginated)
GET    /api/v1/jobs/{id}                 # Get job details
POST   /api/v1/jobs/{id}/analyze         # ATS match analysis
DELETE /api/v1/jobs/{id}                 # Delete job

POST   /api/v1/applications              # Create application
POST   /api/v1/applications/batch        # Batch create
GET    /api/v1/applications              # List applications
PUT    /api/v1/applications/{id}/approve  # Approve for submission
PUT    /api/v1/applications/{id}/status   # Update status

POST   /api/v1/resumes/upload            # Upload resume (PDF/DOCX)
GET    /api/v1/resumes                   # List resumes
POST   /api/v1/resumes/generate          # Generate tailored resume
POST   /api/v1/resumes/{id}/score        # ATS score against job
GET    /api/v1/resumes/{id}/download     # Download as PDF or DOCX

GET    /api/v1/analytics/dashboard       # Dashboard stats
GET    /api/v1/analytics/funnel          # Application funnel
GET    /api/v1/analytics/ats-scores      # Score distribution
GET    /api/v1/analytics/llm-usage       # Token and cost tracking
GET    /api/v1/analytics/timeline        # Daily activity timeline

GET    /api/v1/settings                  # Get settings
PUT    /api/v1/settings                  # Update settings
GET    /api/v1/settings/llm-providers    # Provider status

WS     /ws                              # Real-time event stream
GET    /health                           # Health check
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
  workers/        # Background queue workers
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
docs/             # API docs, integration plan, tools reference
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

### Working

- FastAPI backend with versioned API routes and OpenAPI docs
- React + MUI dashboard with jobs, applications, resumes, analytics, and settings pages
- Application tracking CRUD with approval flow and status lifecycle
- Resume upload with real parsing (PDF/DOCX), skill extraction, and ATS scoring
- Multi-factor ATS scoring engine (skills, keywords, experience, education)
- Analytics endpoints (dashboard stats, funnel, ATS distribution, LLM usage, timeline)
- Redis worker scaffolding and WebSocket progress events
- LLM client with provider fallback chain and Prometheus metrics
- Exa AI semantic job search integration
- Dockerized local environment (backend, frontend, worker, Redis)
- 30+ unit tests and integration tests

### In Progress

- Live platform search execution (LinkedIn, Indeed, Glassdoor scrapers)
- Fully automated browser-based application submission
- LLM-powered resume generation and cover letter pipeline
- Persistent settings and provider health checks

## Responsible Use

This project touches hiring workflows, personal data, and platform automation.

- Review all AI-generated materials before submission
- Respect platform terms, rate limits, and automation policies
- Do not misrepresent qualifications or fabricate experience
- Protect stored credentials and personal profile data
- Keep human approval in the loop unless you have a strong reason not to

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) -- system architecture and data flows
- [docs/API.md](docs/API.md) -- API reference
- [docs/INTEGRATION_PLAN.md](docs/INTEGRATION_PLAN.md) -- integration roadmap
- [docs/TOOLS.md](docs/TOOLS.md) -- tooling reference

## Adding a New Platform

1. Create `backend/app/core/automation/platforms/{name}.py`
2. Implement the `JobPlatform` ABC (`login`, `search`, `scrape_details`, `apply`)
3. Register in `platforms/__init__.py`

## Adding a Resume Template

1. Create `templates/resume/{name}/template.html` + `style.css`
2. Add the template name to `RESUME_TEMPLATES` in `backend/app/config/constants.py`
