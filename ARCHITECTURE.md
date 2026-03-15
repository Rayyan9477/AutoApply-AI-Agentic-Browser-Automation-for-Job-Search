# AutoApply AI — System Architecture v2.0

## Table of Contents
1. [High-Level Architecture](#1-high-level-architecture)
2. [Project Structure](#2-project-structure)
3. [Backend Architecture](#3-backend-architecture)
4. [Frontend Architecture](#4-frontend-architecture)
5. [Core Modules](#5-core-modules)
6. [Data Flow](#6-data-flow)
7. [API Contracts](#7-api-contracts)
8. [Data Models](#8-data-models)
9. [Infrastructure](#9-infrastructure)
10. [Observability](#10-observability)
11. [Migration Plan](#11-migration-plan)

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React + MUI)                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────────┐  │
│  │ Dashboard │ │ Job List │ │ Resume   │ │ Application       │  │
│  │          │ │ & Search │ │ Manager  │ │ Tracker           │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────────┘  │
│       ▲              ▲           ▲              ▲               │
│       │     REST API + WebSocket (real-time)    │               │
└───────┼──────────────┼───────────┼──────────────┼───────────────┘
        │              │           │              │
┌───────┼──────────────┼───────────┼──────────────┼───────────────┐
│       ▼              ▼           ▼              ▼               │
│                    BACKEND (FastAPI)                             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    API Layer (v1)                        │    │
│  │  /jobs  /applications  /resumes  /analytics  /settings  │    │
│  └────────────────────────┬────────────────────────────────┘    │
│                           │                                     │
│  ┌────────────────────────▼────────────────────────────────┐    │
│  │                  Service Layer                          │    │
│  │  JobSearchService  ApplicationService  ResumeService    │    │
│  │  AnalyticsService  QueueService                         │    │
│  └────────────┬───────────┬────────────┬───────────────────┘    │
│               │           │            │                        │
│  ┌────────────▼───┐ ┌─────▼──────┐ ┌──▼──────────────────┐     │
│  │  Core Modules  │ │  LLM Layer │ │  Queue & Workers    │     │
│  │  ┌───────────┐ │ │ ┌────────┐ │ │ ┌────────────────┐ │     │
│  │  │ Browser   │ │ │ │Portkey │ │ │ │ Redis Queue    │ │     │
│  │  │ Automation│ │ │ │Gateway │ │ │ │ ┌────────────┐ │ │     │
│  │  │(browser-  │ │ │ │   │    │ │ │ │ │App Worker  │ │ │     │
│  │  │ use Agent)│ │ │ │   ▼    │ │ │ │ │Scrape Wrkr │ │ │     │
│  │  ├───────────┤ │ │ │LiteLLM│ │ │ │ └────────────┘ │ │     │
│  │  │ Document  │ │ │ │   │    │ │ │ └────────────────┘ │     │
│  │  │ Engine    │ │ │ │   ▼    │ │ └────────────────────┘     │
│  │  │(PDF/DOCX) │ │ │ │OpenAI │ │                              │
│  │  ├───────────┤ │ │ │Groq   │ │                              │
│  │  │ ATS       │ │ │ │Gemini │ │                              │
│  │  │ Scorer    │ │ │ │Local  │ │                              │
│  │  ├───────────┤ │ │ └────────┘ │                              │
│  │  │ Matching  │ │ └────────────┘                              │
│  │  │ (FAISS)   │ │                                             │
│  │  └───────────┘ │                                             │
│  └────────────────┘                                             │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Data Layer                                   │   │
│  │  ┌──────────┐  ┌───────────┐  ┌────────────────────┐    │   │
│  │  │ SQLite/  │  │   Redis   │  │ FAISS Vector       │    │   │
│  │  │ Postgres │  │ Cache+Queue│  │ Indices            │    │   │
│  │  └──────────┘  └───────────┘  └────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │           Observability                                   │   │
│  │  Structlog → Prometheus Metrics → LLM Tracing (Portkey)  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Project Structure

```
AutoApply-AI-Smart-Job-Application-Assistant/
│
├── backend/                          # FastAPI backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI app factory + lifespan
│   │   │
│   │   ├── config/
│   │   │   ├── settings.py           # Pydantic BaseSettings (env-based)
│   │   │   └── constants.py          # App-wide constants
│   │   │
│   │   ├── api/
│   │   │   ├── deps.py               # Shared dependencies (get_db, get_redis)
│   │   │   ├── v1/
│   │   │   │   ├── router.py         # Aggregates all v1 routes
│   │   │   │   ├── jobs.py           # Job search & listing endpoints
│   │   │   │   ├── applications.py   # Application CRUD & queue endpoints
│   │   │   │   ├── resumes.py        # Resume upload, generate, score, download
│   │   │   │   ├── analytics.py      # Dashboard & reporting endpoints
│   │   │   │   └── settings.py       # User settings & LLM config endpoints
│   │   │   └── websocket/
│   │   │       ├── endpoint.py       # WS connection handler
│   │   │       └── events.py         # ConnectionManager for broadcasting
│   │   │
│   │   ├── core/                     # Business logic & domain modules
│   │   │   ├── exceptions.py         # Custom exception hierarchy
│   │   │   ├── db_resilience.py      # DB error mapping & retry decorator
│   │   │   │
│   │   │   ├── automation/           # Browser automation layer
│   │   │   │   ├── agent.py          # browser-use Agent wrapper
│   │   │   │   ├── session_manager.py# Cookie persistence & rotation
│   │   │   │   └── platforms/
│   │   │   │       ├── base.py       # Abstract JobPlatform + JobListing
│   │   │   │       ├── linkedin.py   # LinkedIn integration
│   │   │   │       ├── indeed.py     # Indeed integration
│   │   │   │       ├── glassdoor.py  # Glassdoor integration
│   │   │   │       └── registry.py   # Platform plugin registry
│   │   │   │
│   │   │   ├── documents/            # Document generation & parsing
│   │   │   │   ├── parser.py         # Resume parsing (PDF, DOCX, TXT)
│   │   │   │   ├── generator.py      # Resume/CL generation orchestrator
│   │   │   │   ├── pdf_renderer.py   # HTML→PDF via WeasyPrint
│   │   │   │   ├── docx_renderer.py  # DOCX generation via python-docx
│   │   │   │   └── templates/        # Built-in resume templates + styles
│   │   │   │
│   │   │   ├── ats/                  # ATS scoring & optimization
│   │   │   │   ├── scorer.py         # Multi-factor resume scorer
│   │   │   │   ├── optimizer.py      # LLM-powered resume optimization
│   │   │   │   ├── keyword_analyzer.py # TF-IDF keyword analysis
│   │   │   │   ├── experience_analyzer.py # Experience extraction
│   │   │   │   └── skill_matcher.py  # Skill extraction & matching
│   │   │   │
│   │   │   ├── llm/                  # LLM integration layer
│   │   │   │   ├── client.py         # LiteLLM unified client + Portkey
│   │   │   │   ├── usage_tracker.py  # LLM cost/usage tracking
│   │   │   │   └── prompts/
│   │   │   │       └── cover_letter.py # Cover letter prompt templates
│   │   │   │
│   │   │   ├── job_discovery/        # External job search
│   │   │   │   └── exa_search.py     # Exa AI semantic job search
│   │   │   │
│   │   │   └── matching/             # Job-candidate matching
│   │   │       └── vector_store.py   # FAISS vector operations
│   │   │
│   │   ├── services/                 # Application services (orchestration)
│   │   │   ├── job_search.py         # Multi-platform job search
│   │   │   ├── application.py        # Application lifecycle management
│   │   │   ├── resume.py             # Resume generation & management
│   │   │   ├── analytics.py          # Dashboard data aggregation
│   │   │   └── queue.py              # Redis queue manager
│   │   │
│   │   ├── models/                   # SQLAlchemy ORM models
│   │   │   ├── base.py               # Declarative base + mixins
│   │   │   ├── job.py                # Job listing model
│   │   │   ├── application.py        # Application tracking
│   │   │   ├── resume.py             # Resume records
│   │   │   ├── llm_usage.py          # LLM usage/cost tracking
│   │   │   └── user_settings.py      # User settings/preferences
│   │   │
│   │   ├── schemas/                  # Pydantic request/response schemas
│   │   │   ├── job.py
│   │   │   ├── application.py
│   │   │   ├── resume.py
│   │   │   ├── analytics.py
│   │   │   └── settings.py
│   │   │
│   │   ├── db/                       # Database layer
│   │   │   ├── session.py            # SQLAlchemy async engine + sessions
│   │   │   ├── redis.py              # Redis connection pool manager
│   │   │   └── migrations/           # Alembic migrations
│   │   │
│   │   ├── workers/                  # Background task workers
│   │   │   └── application_worker.py # Processes application queue
│   │   │
│   │   └── observability/            # Monitoring & logging
│   │       ├── logging.py            # Structlog configuration
│   │       ├── metrics.py            # Prometheus metrics definitions
│   │       └── tracing.py            # LLM cost/latency tracking
│   │
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── unit/                     # 30+ unit test files
│   │   ├── integration/              # API integration tests
│   │   └── e2e/                      # End-to-end pipeline tests
│   │
│   ├── alembic.ini
│   └── pyproject.toml
│
├── frontend/                         # React + MUI + Vite
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── theme.ts                  # MUI theme configuration
│   │   │
│   │   ├── components/               # Reusable UI components
│   │   │   ├── layout/               # Sidebar, Header, AppLayout
│   │   │   ├── jobs/                 # JobCard, JobFilters, JobDetail
│   │   │   ├── applications/         # ApplicationCard, ApplicationStatus
│   │   │   ├── resumes/              # ResumeUpload, TemplateSelector, ATSScoreCard
│   │   │   ├── dashboard/            # StatsCards, ApplicationFunnel
│   │   │   └── common/               # LoadingState, ErrorBoundary, ConfirmDialog
│   │   │
│   │   ├── pages/                    # Route-level pages
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── JobSearchPage.tsx
│   │   │   ├── ApplicationsPage.tsx
│   │   │   ├── ResumesPage.tsx
│   │   │   ├── SettingsPage.tsx
│   │   │   └── AnalyticsPage.tsx
│   │   │
│   │   ├── hooks/                    # Custom React hooks
│   │   │   ├── useJobs.ts, useApplications.ts, useResumes.ts
│   │   │   ├── useAnalytics.ts, useSettings.ts
│   │   │   └── useWebSocket.ts       # Auto-reconnecting WS hook
│   │   │
│   │   ├── services/                 # API client layer
│   │   │   ├── api.ts                # Axios instance + interceptors
│   │   │   ├── jobService.ts, applicationService.ts
│   │   │   ├── resumeService.ts, analyticsService.ts
│   │   │   └── settingsService.ts
│   │   │
│   │   ├── store/                    # State management (Zustand)
│   │   │   ├── useJobStore.ts
│   │   │   └── useAppStore.ts
│   │   │
│   │   └── types/                    # TypeScript types
│   │       ├── job.ts, application.ts, resume.ts
│   │       ├── analytics.ts, settings.ts
│   │       └── api.ts
│   │
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── docker/                           # Container configuration
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── nginx.conf                    # Reverse proxy + SPA fallback
│
├── docker-compose.yml                # Production stack
├── docker-compose.dev.yml            # Dev overrides (hot reload)
│
├── templates/                        # Resume & cover letter templates
│   ├── resume/                       # modern, classic, creative, executive, minimal
│   └── cover_letter/                 # standard, technical, creative
│
├── data/                             # Runtime data (gitignored)
│   ├── db/                           # SQLite database file
│   ├── uploads/                      # Uploaded resume files
│   ├── sessions/                     # Browser session cookies
│   ├── vector_indices/               # FAISS index files
│   ├── generated/                    # Generated resumes & cover letters
│   └── logs/                         # Application logs
│
├── docs/                             # Additional documentation
│   ├── API.md
│   ├── INTEGRATION_PLAN.md
│   └── TOOLS.md
│
├── .env.example                      # Environment variable template
├── CLAUDE.md                         # Project conventions for AI
├── ARCHITECTURE.md                   # This file
└── README.md
```

---

## 3. Backend Architecture

### 3.1 Layered Design

```
┌──────────────────────────────────────────┐
│           API Routes (api/v1/)           │  ← HTTP request/response handling
│   Validates input, calls services,       │
│   returns Pydantic schemas               │
├──────────────────────────────────────────┤
│           Services (services/)           │  ← Business logic orchestration
│   Coordinates core modules,              │
│   manages transactions, queues tasks     │
├──────────────────────────────────────────┤
│          Core Modules (core/)            │  ← Domain logic
│   Automation, Documents, ATS, LLM,       │
│   Matching — each self-contained         │
├──────────────────────────────────────────┤
│          Data Layer (db/, models/)        │  ← Persistence
│   SQLAlchemy ORM, Redis, FAISS           │
└──────────────────────────────────────────┘
```

### 3.2 Dependency Injection (FastAPI native)

```python
# api/deps.py
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session

async def get_redis() -> Redis:
    return redis_pool

async def get_llm_client() -> LLMClient:
    return LLMClient(settings.llm)

async def get_job_search_service(
    db: AsyncSession = Depends(get_db),
    llm: LLMClient = Depends(get_llm_client),
) -> JobSearchService:
    return JobSearchService(db=db, llm=llm)
```

### 3.3 Async-First Design

All I/O operations are async:
- Database: `sqlalchemy[asyncio]` with `aiosqlite`
- HTTP: `httpx.AsyncClient`
- Browser: `browser-use` (built on async Playwright)
- Redis: `redis.asyncio`
- LLM calls: `litellm.acompletion()`

---

## 4. Frontend Architecture

### 4.1 Tech Stack
- **React 18** with TypeScript
- **Vite** for build tooling
- **MUI v5** component library
- **Zustand** for state management (lightweight, no boilerplate)
- **React Router v6** for routing
- **Axios** for API calls
- **Recharts** for analytics charts
- **React Query (TanStack Query)** for server state caching

### 4.2 Pages & Routes

| Route | Page | Description |
|---|---|---|
| `/` | DashboardPage | Stats, recent activity, quick actions |
| `/jobs` | JobSearchPage | Search, filter, browse jobs |
| `/jobs/:id` | JobDetailPage | Job details, match score, apply action |
| `/applications` | ApplicationsPage | Track all applications, status filters |
| `/resumes` | ResumesPage | Upload, manage, generate resumes |
| `/analytics` | AnalyticsPage | Charts, funnel, ATS score distribution |
| `/settings` | SettingsPage | LLM config, apply mode, platform auth |

### 4.3 Real-time Updates

WebSocket connection for:
- Browser automation progress (live screenshots, step-by-step status)
- Application status changes
- Queue position updates
- LLM generation progress

---

## 5. Core Modules

### 5.1 Browser Automation (`core/automation/`)

```
┌─────────────────────────────────────────┐
│          BrowserAgent (agent.py)         │
│  Wraps browser-use Agent                │
│  - Configurable LLM (via LiteLLM)       │
│  - Session management                   │
│  - Screenshot capture                   │
│  - Action logging                       │
├─────────────────────────────────────────┤
│       SessionManager (session_mgr.py)   │
│  - Cookie save/load per platform        │
│  - Session rotation & refresh           │
│  - Anti-detection config                │
├─────────────────────────────────────────┤
│    Platform Registry (registry.py)      │
│  - Register/discover platform plugins   │
│  - Factory: get_platform("linkedin")    │
├──────────┬──────────┬───────────────────┤
│ LinkedIn │  Indeed  │  Glassdoor        │
│ .search()│ .search()│  .search()        │
│ .scrape()│ .scrape()│  .scrape()        │
│ .apply() │ .apply() │  .apply()         │
└──────────┴──────────┴───────────────────┘
```

**Platform Plugin Interface:**
```python
class JobPlatform(ABC):
    """Base class for job platform integrations."""

    @abstractmethod
    async def search(self, query: JobSearchQuery) -> list[JobListing]: ...

    @abstractmethod
    async def scrape_details(self, job_url: str) -> JobDetails: ...

    @abstractmethod
    async def apply(self, job: JobDetails, resume_path: Path, cover_letter_path: Path) -> ApplicationResult: ...

    @abstractmethod
    async def login(self, session_manager: SessionManager) -> bool: ...
```

### 5.2 Document Engine (`core/documents/`)

```
Input Resume (PDF/DOCX/TXT)
        │
        ▼
  ┌─────────────┐
  │   Parser     │  PyPDF2, python-docx
  │  (parser.py) │  Extracts structured text
  └──────┬──────┘
         │
         ▼
  ┌──────────────┐     ┌──────────────┐
  │  Generator   │────▶│  LLM Client  │  Tailors content to JD
  │(generator.py)│◀────│  (Portkey +   │
  └──────┬──────┘     │   LiteLLM)   │
         │             └──────────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────┐
│  PDF   │ │  DOCX  │
│Renderer│ │Renderer│
│(Weasy- │ │(python-│
│ Print) │ │  docx) │
└────────┘ └────────┘
    │           │
    ▼           ▼
 resume.pdf  resume.docx
```

**Templates:** 5 pre-built designs (Modern, Classic, Creative, Executive, Minimal)
- HTML + CSS templates rendered to PDF via WeasyPrint
- Parallel DOCX generation via python-docx with matching styles

### 5.3 ATS Engine (`core/ats/`)

```
Resume Text + Job Description
        │
   ┌────┴─────────────────────────┐
   ▼                              ▼
┌──────────────┐          ┌──────────────┐
│  Keyword     │          │  Semantic    │
│  Analyzer    │          │  Scorer      │
│  (TF-IDF)    │          │  (FAISS +    │
│              │          │  SentenceTF) │
└──────┬───────┘          └──────┬───────┘
       │                         │
       ▼                         ▼
┌──────────────────────────────────────┐
│         Composite ATS Score          │
│   keyword: 40% | semantic: 35%      │
│   skills: 15%  | format: 10%        │
├──────────────────────────────────────┤
│        Score < threshold?            │
│        YES → Optimizer (LLM)        │
│        NO  → Pass through           │
└──────────────────────────────────────┘
```

### 5.4 LLM Layer (`core/llm/`)

```
Application Code
       │
       ▼
┌──────────────────┐
│  LLMClient       │  Unified interface
│  (client.py)     │  - completion()
│                  │  - acompletion()
│                  │  - stream()
├──────────────────┤
│  Portkey Gateway │  Caching, fallbacks,
│  (gateway.py)    │  load balancing,
│                  │  observability
├──────────────────┤
│  LiteLLM         │  Provider abstraction
│                  │  100+ providers
├────────┬─────────┤
│OpenAI  │ Groq    │ Gemini │ Local  │ OpenRouter │
│gpt-4o  │ llama   │ gemini │ GGUF   │ any model  │
└────────┴─────────┴────────┴────────┴────────────┘
```

**Provider Priority (configurable):**
1. User's preferred provider (from settings)
2. Portkey routes to best available
3. Fallback chain: primary → secondary → local

### 5.5 Queue System (`workers/`)

```
┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│  API/Service │────▶│   Redis Queue    │────▶│   Workers    │
│  enqueue()   │     │                 │     │              │
└──────────────┘     │  apply_queue    │     │  app_worker  │
                     │  scrape_queue   │     │  scrape_wrkr │
                     │  generate_queue │     │              │
                     └─────────────────┘     └──────┬───────┘
                                                    │
                                              ┌─────▼─────┐
                                              │ WebSocket  │
                                              │ Progress   │
                                              │ Updates    │
                                              └───────────┘
```

---

## 6. Data Flow

### 6.1 Job Search Flow
```
User enters search query in React UI
  → POST /api/v1/jobs/search
    → JobSearchService.search()
      → PlatformRegistry.get_platforms(enabled_platforms)
      → asyncio.gather(
          linkedin.search(query),
          indeed.search(query),
          glassdoor.search(query)
        )
      → Each platform uses browser-use Agent to:
          1. Navigate to search page
          2. Fill search form
          3. Extract job listings
          4. Return structured JobListing[]
      → Deduplicate results
      → Store in DB
      → Calculate match scores (FAISS similarity)
    → Return paginated results to frontend
  → Frontend renders JobList with JobCards
```

### 6.2 Application Flow (Configurable Mode)
```
User selects job(s) to apply
  → POST /api/v1/applications (or /batch)
    → ApplicationService.create_application()
      → Check apply_mode from settings:

        MODE: "autonomous"
          → Enqueue to Redis apply_queue immediately

        MODE: "review"
          → Create application with status="pending_review"
          → Return to frontend for user review
          → User clicks "Approve" → enqueue

        MODE: "batch"
          → Create application with status="queued"
          → User reviews batch → "Approve All" → enqueue all

  Worker picks up from queue:
    → Generate tailored resume (LLM)
    → ATS score against JD
    → If score < threshold: optimize (LLM) → re-score
    → Generate cover letter (LLM)
    → Render to PDF + DOCX
    → browser-use Agent:
        1. Navigate to job application page
        2. Fill form fields
        3. Upload resume
        4. Submit application
        5. Screenshot confirmation
    → Update application status in DB
    → WebSocket: notify frontend of completion
```

### 6.3 Resume Generation Flow
```
POST /api/v1/resumes/generate { job_id, template_id }
  → ResumeService.generate()
    → Parse base resume (parser.py)
    → Fetch job details from DB
    → LLMClient.completion(prompt=resume_tailor_prompt)
      → Portkey Gateway → LiteLLM → Provider
    → Render to PDF (WeasyPrint) + DOCX (python-docx)
    → Store file paths in DB
    → Return download URLs
```

---

## 7. API Contracts

### 7.1 Jobs

```
POST   /api/v1/jobs/search
  Body: { keywords: str[], location: str, platforms: str[], remote_only: bool }
  Response: { jobs: JobListing[], total: int, page: int }

GET    /api/v1/jobs?status=new&sort=match_score&page=1&limit=20
GET    /api/v1/jobs/{id}
POST   /api/v1/jobs/{id}/analyze
DELETE /api/v1/jobs/{id}
```

### 7.2 Applications

```
POST   /api/v1/applications
  Body: { job_id: str, resume_id: str, template_id: str, mode: "auto"|"review" }

POST   /api/v1/applications/batch
  Body: { job_ids: str[], resume_id: str, template_id: str }

GET    /api/v1/applications?status=pending|applied|interview|rejected
GET    /api/v1/applications/{id}
PUT    /api/v1/applications/{id}/approve    # For review mode
PUT    /api/v1/applications/{id}/status
```

### 7.3 Resumes

```
POST   /api/v1/resumes/upload              # Upload base resume
  Body: multipart/form-data (file)

GET    /api/v1/resumes                      # List all resumes
POST   /api/v1/resumes/generate             # Generate tailored resume
  Body: { job_id: str, template_id: str, base_resume_id: str }

POST   /api/v1/resumes/{id}/score           # ATS score
  Body: { job_description: str }

POST   /api/v1/resumes/{id}/optimize        # Optimize for ATS
GET    /api/v1/resumes/{id}/download?format=pdf|docx
```

### 7.4 Analytics

```
GET    /api/v1/analytics/dashboard          # Summary stats
GET    /api/v1/analytics/funnel             # Application funnel
GET    /api/v1/analytics/ats-scores         # Score distribution
GET    /api/v1/analytics/llm-usage          # Token/cost tracking
GET    /api/v1/analytics/timeline           # Applications over time
```

### 7.5 Settings

```
GET    /api/v1/settings
PUT    /api/v1/settings
  Body: {
    apply_mode: "autonomous"|"review"|"batch",
    max_parallel: 1-5,
    min_ats_score: 0.0-1.0,
    preferred_llm_provider: str,
    platforms_enabled: str[]
  }

GET    /api/v1/settings/llm-providers       # Available providers + status
PUT    /api/v1/settings/llm-providers       # Configure API keys
```

### 7.6 WebSocket

```
WS     /ws/events
  Messages (server → client):
    { type: "application_progress", data: { id, step, status, screenshot_url } }
    { type: "application_complete", data: { id, status, result } }
    { type: "job_search_progress", data: { platform, found, total } }
    { type: "generation_progress", data: { id, step, status } }
    { type: "queue_update", data: { pending, processing, completed } }
```

---

## 8. Data Models

### 8.1 SQLAlchemy Models

```python
class Job(Base):
    __tablename__ = "jobs"
    id: str                    # UUID
    platform: str              # linkedin, indeed, glassdoor
    platform_job_id: str       # Platform-specific ID
    title: str
    company: str
    location: str
    url: str
    description: str
    salary_range: str | None
    job_type: str              # full-time, part-time, contract
    remote: bool
    posted_date: datetime
    match_score: float         # Candidate match score
    skills_required: JSON      # Extracted skills list
    status: str                # new, saved, applied, hidden
    created_at: datetime
    updated_at: datetime

class Application(Base):
    __tablename__ = "applications"
    id: str
    job_id: str                # FK → jobs.id
    resume_id: str             # FK → resumes.id
    cover_letter_path: str
    status: str                # queued, pending_review, applying, applied,
                               # interview, rejected, offer, withdrawn
    apply_mode: str            # autonomous, review, batch
    ats_score: float
    applied_at: datetime
    response_date: datetime | None
    notes: str
    browser_screenshots: JSON  # List of screenshot paths
    created_at: datetime

class Resume(Base):
    __tablename__ = "resumes"
    id: str
    name: str                  # User-friendly name
    type: str                  # base, tailored
    base_resume_id: str | None # FK → self (if tailored)
    job_id: str | None         # FK → jobs.id (if tailored)
    template_id: str
    file_path_pdf: str
    file_path_docx: str
    ats_score: float | None
    content_text: str          # Extracted text for search
    created_at: datetime

class LLMUsage(Base):
    __tablename__ = "llm_usage"
    id: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    latency_ms: int
    purpose: str               # resume_tailor, cover_letter, ats_optimize, job_analysis
    created_at: datetime

class UserSettings(Base):
    __tablename__ = "user_settings"
    id: str
    apply_mode: str
    max_parallel: int
    min_ats_score: float
    preferred_provider: str
    platforms_enabled: JSON
    candidate_profile: JSON
    created_at: datetime
    updated_at: datetime
```

---

## 9. Infrastructure

### 9.1 Docker Compose

```yaml
services:
  backend:
    build: ./docker/Dockerfile.backend
    ports: ["8000:8000"]
    env_file: .env
    volumes:
      - ./data:/app/data
      - ./templates:/app/templates
    depends_on: [redis]

  frontend:
    build: ./docker/Dockerfile.frontend
    ports: ["3000:80"]
    depends_on: [backend]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    volumes:
      - redis_data:/data

  worker:
    build: ./docker/Dockerfile.backend
    command: python -m app.workers.application_worker
    env_file: .env
    volumes:
      - ./data:/app/data
    depends_on: [redis, backend]

volumes:
  redis_data:
```

### 9.2 Environment Variables

```env
# Database
DATABASE_URL=sqlite+aiosqlite:///data/db/autoapply.db
REDIS_URL=redis://localhost:6379/0

# LLM Providers
PORTKEY_API_KEY=
OPENAI_API_KEY=
GROQ_API_KEY=
GEMINI_API_KEY=
OPENROUTER_API_KEY=
GITHUB_TOKEN=

# Browser
BROWSER_HEADLESS=true
BROWSER_MAX_PARALLEL=3

# App
APPLY_MODE=review          # autonomous, review, batch
MIN_ATS_SCORE=0.75
LOG_LEVEL=INFO
```

---

## 10. Observability

### 10.1 Logging (Structlog)
- JSON-formatted structured logs
- Context-bound loggers per request
- Log levels: DEBUG, INFO, WARNING, ERROR

### 10.2 Metrics (Prometheus)
- `autoapply_applications_total{status, platform}` — counter
- `autoapply_ats_score{template}` — histogram
- `autoapply_llm_latency_seconds{provider, model}` — histogram
- `autoapply_llm_tokens_total{provider, model, direction}` — counter
- `autoapply_llm_cost_usd{provider, model}` — counter
- `autoapply_browser_actions_total{platform, action}` — counter
- `autoapply_queue_depth{queue}` — gauge

### 10.3 LLM Tracing (Portkey built-in)
- Per-call token usage and cost
- Latency tracking
- Request/response logging
- Provider fallback events
- Budget alerts

---

## 11. Migration Plan

### Phase 1: Foundation (Backend skeleton + cleanup)
1. Delete obsolete files from current codebase
2. Create new `backend/` directory structure
3. Set up FastAPI app factory with config
4. Migrate SQLAlchemy models (async)
5. Set up Redis connection
6. Implement health check endpoint

### Phase 2: Core Modules
1. Port ATS scorer to `core/ats/`
2. Port document parser to `core/documents/`
3. Implement LiteLLM + Portkey client in `core/llm/`
4. Port FAISS vector store to `core/matching/`
5. Build platform plugin system in `core/automation/`

### Phase 3: API + Services
1. Build all API routes with Pydantic schemas
2. Implement service layer orchestration
3. Set up Redis queue + workers
4. Add WebSocket events

### Phase 4: Browser Automation
1. Implement browser-use Agent wrapper
2. Build LinkedIn platform plugin
3. Build Indeed platform plugin
4. Build Glassdoor platform plugin
5. Implement session management

### Phase 5: Document Generation
1. Create 5 HTML/CSS resume templates
2. Implement WeasyPrint PDF renderer
3. Implement DOCX renderer
4. Build cover letter templates

### Phase 6: Frontend
1. React + Vite + MUI project setup
2. Dashboard page
3. Job search page
4. Applications page
5. Resume management page
6. Settings page
7. WebSocket integration

### Phase 7: Observability + Deployment
1. Structlog configuration
2. Prometheus metrics
3. Docker compose setup
4. Cloud deployment config
