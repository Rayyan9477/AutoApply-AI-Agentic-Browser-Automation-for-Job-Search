# AutoApply AI — Bug Log

Living log of bugs found during testing. The four **P1/P2** items below were found in the
2026-07-10 live end-to-end pass (Playwright driving the real SPA + Vite proxy + live FastAPI +
Redis + a fresh Alembic-migrated DB) and have already been **fixed with TDD** (kept here as a
record). The **deferred** items are minor and intentionally left for a later cleanup pass.

Legend: ✅ Fixed & verified · 🔵 Open (deferred) · Sev: P1 critical · P2 major · P3 minor · P4 polish

---

## Fixed this pass

### BUG-001 — ✅ P1 — Logged out on every hard refresh (and multi-tab)
- **Symptom:** any hard reload of an authenticated page bounced the user to `/login`.
- **Root cause:** `AuthProvider` boot effect called `authService.refresh()` directly, bypassing the
  single-flight guard in `services/api.ts`. React StrictMode's dev double-invoke (and multiple tabs
  in prod) fired two concurrent `POST /auth/refresh`; the backend rotates the refresh token and its
  reuse-detection **revokes the whole token family** on the second call → session cleared.
- **Evidence:** network trace on reload = `refresh 200` immediately followed by `refresh 401`.
- **Fix:** exported `refreshAccessToken` from `services/api.ts`; `AuthProvider` now uses the shared
  single-flight so concurrent boots collapse to one refresh. Test: `__tests__/auth/authBootstrap.test.tsx`.

### BUG-002 — ✅ P2 — New users skipped onboarding
- **Symptom:** after registering, users landed on `/dashboard`, never seeing the onboarding wizard.
- **Root cause:** `PublicOnly` hard-redirected any authenticated user to `/dashboard`, racing/
  overriding `RegisterPage`'s `navigate('/onboarding')`.
- **Fix:** `PublicOnly` gained a `redirectTo` prop (default `/dashboard`); the register route uses
  `redirectTo="/onboarding"`. Test: `__tests__/auth/publicOnly.test.tsx`.

### BUG-003 — ✅ P2 — ATS scores shown as "0"/"1" and always colored red
- **Symptom:** every ATS score on Dashboard / Applications / App-detail / Résumés rendered as `0`
  or `1` and used the "rejected" (red) color band.
- **Root cause:** the API/DB store ATS on a **0–1 scale**, but those views rendered a bare
  `Math.round(score)` and passed it to `atsColor` (whose bands are 85/75/65 = 0–100). `JobSearchPage`
  and `SettingsPage` already multiplied by 100; the others did not. Masked in tests because fixtures
  used 0–100 values and never asserted the rendered number.
- **Fix:** added `atsPercent(score) = Math.round((score ?? 0) * 100)` in `lib/status.ts`, used at all
  display sites; corrected the test fixtures to 0–1. Test: `__tests__/lib/status.test.ts` +
  `ApplicationsPage.test.tsx`.
- **Convention (important):** all ATS / match scores are **0–1 in the API → multiply by 100 to display.**

### BUG-004 — ✅ P2 — App-detail page showed "Untitled role / —"
- **Symptom:** the application detail screen showed "Untitled role" and no company.
- **Root cause:** `GET /applications/{id}` returned `job_title`/`company` = null — only the list
  endpoint eager-loaded the `job` relation and hydrated them.
- **Fix:** `get_application` now `selectinload(Application.job)`; new shared `application_to_response()`
  helper (defensive — hydrates only when `.job` is loaded) used by list/get/create/approve/update.
  Test: `tests/integration/test_applications_api.py::...includes_job_title_and_company`.

---

## Fixed 2026-07-17 (were deferred nits — now all closed, TDD)

### BUG-005 — ✅ P4 — `GET /auth/refresh 401` logs to console on public pages
- **Fix:** added a non-sensitive `aa_session_hint` localStorage marker (set on `setAuth`, cleared on
  `clear`). `AuthProvider` now skips the boot refresh probe entirely when the hint is absent (a
  first-time / logged-out visitor), so no guaranteed 401 fires. A returning device still probes once.
  Test: `__tests__/auth/authBootstrap.test.tsx` ("skips the probe … no session hint").

### BUG-006 — ✅ P4 — Dashboard greeting pluralization: "1 roles"
- **Fix:** `DashboardPage` greeting now renders `role`/`roles` based on `applications_applied === 1`.
  Test: `__tests__/pages/DashboardPage.test.tsx` (greeting pluralization).

### BUG-007 — ✅ P4 — `/admin` header breadcrumb shows "AutoApply AI"
- **Fix:** added `'/admin': 'System health'` to the `CRUMB` map in `components/layout/Header.tsx`.
  Test: `__tests__/components/Header.test.tsx`.

### BUG-008 — ✅ P3 — Job search empty-state copy after a zero-result search
- **Fix:** `JobSearchPage` now branches on `search.isSuccess` — a completed search that matched
  nothing shows "No matching roles / …try broadening…", distinct from the pre-search "No jobs yet".
  Test: `__tests__/pages/JobSearchPage.test.tsx` (distinguishes the two empty states).

### BUG-009 — ✅ P2 — Missing `GET /resumes/{id}` and `DELETE /resumes/{id}` endpoints
- **Symptom:** Single resume retrieval and resume deletion were absent from the API route layer despite being documented and needed for resume lifecycle management.
- **Root cause:** `resumes.py` implemented `POST /upload`, `GET /`, `POST /generate`, `POST /{id}/score`, `POST /{id}/optimize`, `GET /{id}/download`, `GET /{id}/profile-data`, but lacked `GET /{id}` and `DELETE /{id}`.
- **Fix:** Added `get_resume` and `delete_resume` (with storage cleanup of PDF/DOCX files) to `services/resume.py` and `api/v1/resumes.py`. Client functions added to `frontend/src/services/resumeService.ts`. Integration test: `tests/integration/test_resumes_api.py::TestGetResumeDetailAPI` + `TestDeleteResumeAPI`.

### BUG-010 — ✅ P2 — Missing `DELETE /applications/{id}` endpoint
- **Symptom:** Users had no way to delete an application from their pipeline (only account-wide purge existed).
- **Root cause:** `delete_application` was absent in both `services/application.py` and `api/v1/applications.py`.
- **Fix:** Implemented `delete_application` in service and API layers; added frontend client in `frontend/src/services/applicationService.ts`. Integration test: `tests/integration/test_applications_api.py::TestDeleteApplication`.

### BUG-011 — ✅ P3 — Standalone `Dockerfile.backend` missing `COPY templates/`
- **Symptom:** Building `docker/Dockerfile.backend` directly produced images where resume/cover-letter generation raised `TemplateError` without volume mounting.
- **Root cause:** `Dockerfile.api` and `Dockerfile.worker` copied `templates/`, but `Dockerfile.backend` omitted it.
- **Fix:** Added `COPY templates/ ./templates/` to `docker/Dockerfile.backend`.

### BUG-012 — ✅ P3 — `docker/nginx.conf` missing `/health` reverse proxy
- **Symptom:** Container health checks or monitoring systems probing the frontend proxy (port 3000) for `/health` received 404.
- **Root cause:** `docker/nginx.conf` proxied `/api/`, `/ws`, and `/metrics`, but omitted `/health`.
- **Fix:** Added `location /health { proxy_pass http://backend:8000; }` in `docker/nginx.conf`.

---

## Fixed in Pipeline Integrity & Live-Apply Readiness (2026-11-23, Tasks 1–12)

### BUG-013 — ✅ P1 — Simulated runs counted as real applications (Task 1)
- **Symptom:** When `BROWSER__LIVE_APPLY=false`, placeholder submissions marked applications as `APPLIED`, set `applied_at`, distorted conversion funnel/metrics, and prevented creating new applications for the same job due to the active application unique constraint.
- **Root cause:** `_apply` blindly transitioned successful placeholder runs to `APPLIED`. `ApplicationStatus` lacked a `SIMULATED` terminal state, and the partial unique index `uq_app_active_job` didn't exclude simulated runs.
- **Fix:** Added `SIMULATED = "simulated"` to `ApplicationStatus` and `_TERMINAL_STATES`; created migration `0007` to recreate `uq_app_active_job` excluding `('rejected', 'withdrawn', 'failed', 'simulated')`; branched `_apply` on `PLACEHOLDER_CONFIRMATION` to set `SIMULATED`, `applied_at=None`, and explanatory notes; excluded simulated applications from dashboard counts and funnel stages. Tests: `tests/unit/test_worker_simulated.py`, `tests/integration/test_migration_0007.py`.

### BUG-014 — ✅ P1 — Duplicate application create resets status and re-dispatches (Task 2)
- **Symptom:** Calling `POST /api/v1/applications` for a job that already had an existing application returned 201 Created, reset its status to `pending_review`, and re-enqueued background apply worker tasks.
- **Root cause:** `create_application` returned only the model instance without signalling whether it was newly created or existing, and the route unconditionally called `dispatch_for_mode` and returned 201.
- **Fix:** Modified `create_application` to return `tuple[Application, bool]` (`created`); route returns 200 with existing row untouched and skips dispatch when `created is False`. Test: `tests/integration/test_applications_api.py::test_duplicate_create_returns_existing_unchanged`.

### BUG-015 — ✅ P2 — User settings ignored by application create and worker ATS gate (Task 3)
- **Symptom:** Applications were created with hardcoded `review` mode regardless of user preference in `UserSettings`, created applications had `resume_id=None` unless explicitly passed, and the worker ATS gate checked against a hardcoded threshold without persisting the calculated score.
- **Root cause:** `UserSettings` table was disconnected from pipeline dispatch; `ApplicationCreate` had no defaulting logic against user settings or tenant base resume; worker ATS gate evaluated against a fixed threshold and discarded the score.
- **Fix:** Created `services/user_prefs.py` with `get_user_settings` and `default_resume_id`; updated `create_application` and `create_batch` to default `apply_mode` and `resume_id`; updated worker `_ats_gate_ok` to evaluate against `settings.min_ats_score` and persist `ats_score` to the application record. Tests: `tests/unit/test_user_prefs.py`, `tests/integration/test_applications_defaults.py`.

### BUG-016 — ✅ P1 — Uncontrolled status transitions, missing retry endpoint, and worker race on withdrawn applications (Task 4)
- **Symptom:** Users could update applications to arbitrary statuses bypassing lifecycle rules; failed, simulated, or withdrawn applications could not be retried; applications withdrawn while waiting in queue were still submitted by the background worker.
- **Root cause:** `update_status` had no transition validation; there was no retry endpoint; worker `_apply` did not recheck application status after dequeueing from Redis.
- **Fix:** Enforced `ALLOWED_TRANSITIONS` state machine in `services/application.py` (rejecting invalid transitions with `IntegrityError` / 409); implemented `retry_application` and `POST /api/v1/applications/{app_id}/retry`; guarded worker `_apply` to only proceed if status is `QUEUED` or `APPROVED`. Tests: `tests/unit/test_status_transitions.py`, `tests/integration/test_applications_retry.py`.

### BUG-017 — ✅ P2 — Stuck applications orphaned indefinitely without automated reaper (Task 5)
- **Symptom:** Applications left in `APPLYING` (due to worker crash/timeout) or `APPROVED`/`QUEUED` (due to Redis job loss) remained stuck permanently with no recovery mechanism.
- **Root cause:** Lack of periodic reaper task to clean up expired in-flight applications.
- **Fix:** Created `services/reaper.py` with `reap_stuck_applications`, transitioning stale `APPLYING` (>45m; the plan said 15m, but that is shorter than the 30-minute worker `job_timeout` and would reap live runs) to `FAILED` with notes `"Worker lost while applying (reaped)"`, and re-enqueueing stale `APPROVED` or autonomous `QUEUED` (>30m); scheduled as cron at minutes 5, 25, 45 in Arq worker. Test: `tests/unit/test_reaper.py`.

### BUG-018 — ✅ P2 — Queue depth inspection crashed with `WRONGTYPE` on Arq 0.28 sorted set (Task 6)
- **Symptom:** Queue depth monitoring in dispatch, worker tasks, and anomaly detection crashed with Redis error `WRONGTYPE Operation against a key holding the wrong kind of value`.
- **Root cause:** Arq 0.28 implements `arq:queue` as a sorted set (zset), but codebase called `redis.llen("arq:queue")` (list operation).
- **Fix:** Replaced `llen` with `zcard` in `services/dispatch.py`, `workers/tasks.py`, and `core/harness/anomaly.py`. Test: `tests/unit/test_queue_depth_zcard.py`.

### BUG-019 — ✅ P1 — ATS score capped at 0.70, below the default 0.75 gate (Task 7)
- **Symptom:** No résumé could reach the default `min_ats_score` of 0.75, so every scored application would fail the worker's ATS gate. ATS scoring was also duplicated across `resume.py` and `job_search.py`, and `analyze_job` loaded spaCy on every request and never persisted `job.match_score`.
- **Root cause:** `_score_with_full_engine` always passed `"experience": []`, so `ExperienceAnalyzer` scored 0 and its weight was lost (overall max 0.70). Separately, the keyword analyzer gives 30% weight to word-vector similarity, which is 0 on `en_core_web_sm` (no vectors), capping the keyword score at 0.70. There was no date-range or degree extraction.
- **Fix:** Extracted `extract_sections` and built unified `core/ats/profile.py` (`extract_candidate_profile`) and `core/ats/engine.py` (`score_resume_against_job`); renormalized keyword analysis when vectors are absent; renormalized score weights and added constructive feedback when experience section is missing; updated `resume.py` and `job_search.py` to use shared engine and persist `job.match_score`. Tests: `tests/unit/test_ats_profile.py`, `tests/unit/test_ats_engine.py`, `tests/unit/test_keyword_analyzer.py`.

### BUG-020 — ✅ P2 — Board search (LinkedIn/Indeed/Glassdoor) always failed, silently (Task 8)
- **Symptom:** On the installed `browser-use` 0.11.5 every board search failed. `search_jobs` caught the error and only logged it, so users silently got Exa-only results with no indication why. The error was re-labelled "browser-use package not installed".
- **Root cause:** `BrowserAgent` imported the removed `BrowserConfig` API and built a `langchain_openai.ChatOpenAI` LLM; `services/job_search.py` logged and dropped per-platform failures instead of returning them.
- **Fix:** Ported `BrowserAgent` to `browser-use` 0.11.5 using `BrowserProfile` and `BrowserSession` via runtime factory; preserved original exceptions as `BrowserError`; added `warnings: list[str]` to `JobSearchResponse` so platform search failures are isolated and returned alongside successful Exa results. Tests: `tests/unit/test_browser_agent.py`, `tests/integration/test_job_search_warnings.py`.

### BUG-021 — ✅ P1 — Exa and direct career-site jobs unappliable due to platform credential requirement (Task 9)
- **Symptom:** Applying to jobs discovered via Exa (e.g. Greenhouse, Lever, Workday) failed at the prerequisite check with `ApplyPrerequisiteError("No saved {platform} session — assisted login required")`, preventing automated applications to career sites.
- **Root cause:** `run_apply` required a stored session keyed on `job.platform` for every job; `allowed_domains` did not cover ATS redirect domains; the résumé file was not allow-listed for upload.
- **Fix:** Created `core/automation/runtime/targets.py` (`resolve_apply_target`) to classify job URLs: job board platforms (LinkedIn, Indeed, Glassdoor) require stored sessions, whereas career site URLs do not (`requires_session=False`); added `allowed_domains` including host and ATS redirect domains (`ATS_DOMAINS`); forwarded `available_file_paths` containing résumé path for file uploads. Tests: `tests/unit/test_apply_targets.py`, `tests/unit/test_run_apply_prereqs.py`.

### BUG-022 — ✅ P1 — Live browser automation missing anti-bot / CAPTCHA intervention tool and session expiry validation (Task 10)
- **Symptom:** When the browser agent encountered CAPTCHA, 2FA, or login walls, it had no tool to invoke the human intervention rendezvous; `_GUARDRAILS` told it to stop and report, so the intervention modal could never open from a real run. Expired platform sessions were loaded and attempted instead of failing fast.
- **Root cause:** Redis intervention rendezvous existed in backend/frontend but was never exposed as a callable tool to the `browser-use` agent; `run_apply` did not check `expires_at` on platform sessions; `browser-use` dependency had a loose version pin.
- **Fix:** Created `core/automation/runtime/tools.py` (`build_apply_tools`) providing `request_human_help` tool hooked into Redis intervention rendezvous; updated `_GUARDRAILS` in `apply.py`; added session expiration validation in `run_apply`; pinned `browser-use==0.11.5` in `pyproject.toml`. Test: `tests/unit/test_apply_tools.py` (help tool + `test_expired_session_is_prerequisite_error`). Not yet exercised against a live browser.

### BUG-023 — ✅ P2 — Frontend query cache bleed on sign-out, missing `simulated` status, client-forced apply mode, and analyze without a résumé (Task 11)
- **Symptom:** Signing out did not purge the TanStack Query cache, so the next user on a shared browser could see the previous user's data; `simulated` applications had no status label; Apply from job search sent its own `apply_mode`, overriding the user's Settings; the job drawer's analyze call sent no `resume_id`, so it always scored 0 against the real backend; search platform `warnings` were ignored.
- **Root cause:** `Sidebar.tsx` sign-out and the refresh-failure logout in `api.ts` did not call `queryClient.clear()` (the client was created inside `main.tsx`); `status.ts` and `types/application.ts` lacked `simulated`; `JobSearchPage` `onApply` posted `apply_mode`; `jobService.analyzeJob` took no résumé id; the search UI dropped `warnings`.
- **Fix:** Singleton `queryClient` in `frontend/src/lib/queryClient.ts`, cleared on sign-out and refresh failure; `simulated` status label and tone; `onApply` posts `{ job_id }` only; `analyzeJob(jobId, resumeId?)` sends `resume_id` with the newest base résumé from `useResumes`; warnings shown as an info toast. Tests: `__tests__/components/Sidebar.test.tsx`, `__tests__/lib/status.test.ts`, `__tests__/auth/refreshInterceptor.test.ts`, `__tests__/pages/JobSearchPage.test.tsx`.

### BUG-024 — ✅ P2 — Frontend lacked application retry action, lifecycle status transitions, and platform session management UI (Task 12)
- **Symptom:** "Re-run" on the application detail page only PUT `status=queued`, which never re-dispatched the run (and is now rejected by the Task 4 state machine); there was no control to move an application to interview/offer/rejected; users had no way to import Playwright `storage_state.json` cookies or view connected platform sessions without manual API calls.
- **Root cause:** No frontend client for `POST /applications/{id}/retry` or for the `platform_sessions` endpoints, and no UI for manual status transitions.
- **Fix:** Added `retryApplication` and `updateStatus` with `ALLOWED_TRANSITIONS` mirroring backend; added "Re-run" and "Move to…" controls on `AppDetailPage`; implemented `platformSessionService`, `usePlatformSessions`, and `ConnectedPlatformsCard` in `SettingsPage` allowing import, validation, listing, and disconnect of platform cookies. Tests: `ConnectedPlatformsCard.test.tsx`, `nextStatuses.test.ts`, `AppDetailPage.test.tsx`.

---

## Fixed in Hardening & Product Batch (2026-11-24, Waves 0, A, B, C)

### BUG-025 — ✅ P1 — Unenforced / fail-open tenant isolation on unscoped queries (Task A1)
- **Symptom:** When code executed without an active tenant context (`current_user_id.get() is None`), ORM `SELECT`, `UPDATE`, and `DELETE` queries on `TenantMixin` entities executed against the entire database without a tenant predicate, risking cross-tenant data leakage or corruption.
- **Root cause:** Ambient SQL listener in `db/tenant.py` only injected `WHERE user_id = :current_user_id` when `current_user_id` was non-None, failing open when context was unset. Bulk `UPDATE` and `DELETE` operations were completely uninspected.
- **Fix:** Switched tenant filter to fail-closed. Unscoped queries touching `TenantMixin` tables now raise `TenantScopeError(RuntimeError)` (yielding HTTP 500), unless explicitly exempted via `skip_tenant_filter` execution options or `tenant_bypass()`. Added `tenant_as(user_id)` context manager for background workers and bulk operation guards. Tests: `tests/unit/test_tenant_fail_closed.py`.

### BUG-026 — ✅ P1 — Global unpartitioned domain skills allowing cross-tenant steering (Task A2)
- **Symptom:** Learned site navigation heuristics (`DomainSkill`) and feedback (`SkillFeedback`) were shared globally across all users, allowing one user's agent runs to steer or poison another user's browser automation.
- **Root cause:** `DomainSkill` did not inherit `TenantMixin`, lacking `user_id` isolation. Feedback recording accepted foreign skill IDs.
- **Fix:** Added `TenantMixin` (`user_id NOT NULL`) and unique constraint `uq_domain_skill_user_version` to `DomainSkill` in migration `0008`; purged legacy unowned global rows (operators instructed to back up `domain_skills` prior to applying); scoped `load_skills` and `add_feedback` strictly to `user_id`; hardened guidance injection with 500-char limits, C0/C1 control and format character stripping, and fence neutralization. Tests: `tests/unit/test_skills_per_user.py`, `tests/integration/test_migration_0008.py`.

### BUG-027 — ✅ P1 — Uncapped LLM token spending without per-user budget enforcement (Task A3, B3)
- **Symptom:** Users had no monthly spending limits, creating runaway API cost risks from infinite agent loops or large document tailoring batches.
- **Root cause:** Lack of budget tracking and gate checks before LLM invocation.
- **Fix:** Added `LLM__USER_MONTHLY_BUDGET_USD` setting (default $5.0 per calendar month UTC; `<=0` disables); enforced pre-run budget check via `assert_within_budget(user_id)` in client, generator, and agent loops; mapped `LLMBudgetExceededError` to HTTP 402 Payment Required (`LLM_BUDGET_EXCEEDED`); worker fails over-budget applications terminally (`FAILED`) with note and skips post-run evaluation; exposed `GET /api/v1/analytics/llm-budget` and wired Header spend pill with amber/red budget indicators. Tests: `tests/unit/test_llm_budget.py`, `tests/integration/test_llm_budget_api.py`, `tests/unit/test_worker_budget.py`.

### BUG-028 — ✅ P2 — Synchronous multi-platform scraping blocking HTTP search requests (Task B1, B2)
- **Symptom:** Initiating job searches for LinkedIn, Indeed, or Glassdoor executed browser-use scrapers synchronously during the HTTP request, often taking 30–90+ seconds and risking gateway timeouts.
- **Root cause:** Search route awaited `_search_board` inline for each platform before returning.
- **Fix:** Offloaded board searches to Arq background worker (`search_boards`) while keeping Exa AI semantic search synchronous; published per-board `job_search_progress` and final `job_search_complete` WebSocket events; implemented worker heartbeat fallback (`arq:queue:health-check`) running inline bounded search if Redis or worker pool is offline; added `BoardSearchChips` with live status and job list pagination in frontend. Tests: `tests/integration/test_job_search_async.py`, `tests/unit/test_search_boards_worker.py`.

### BUG-029 — ✅ P2 — Timezone offset drift and aware datetimes on PostgreSQL (Task W0-1, C1)
- **Symptom:** Datetime columns stored timezone offsets or varied between SQLite and PostgreSQL, leading to incorrect comparisons across dialects and timezone-aware bind errors.
- **Root cause:** Direct use of SQLAlchemy `DateTime` without timezone normalization; asyncpg engine didn't force UTC session settings.
- **Fix:** Created `UTCDateTime` TypeDecorator in `app/models/base.py` and converted all model `DateTime` columns to use it, normalising all aware binds to naive UTC; configured asyncpg engine with `connect_args={"server_settings": {"timezone": "UTC"}}`; added opt-in PostgreSQL test recipe via `AUTOAPPLY_TEST_DATABASE_URL` with per-test TRUNCATE. Tests: `tests/unit/test_utc_datetime.py`, `tests/unit/test_pg_guard.py`.

### BUG-030 — ✅ P2 — Missing cover letter download endpoint and UI card (Task A5)
- **Symptom:** Tailored cover letters could be generated via API, but users had no mechanism to download them from the UI or API.
- **Root cause:** Missing `GET /applications/{id}/cover-letter/download` endpoint and missing frontend cover letter component.
- **Fix:** Implemented download endpoint streaming signed PDF/DOCX files with tempfile cleanup via `BackgroundTask`; built `CoverLetterCard` in `AppDetailPage` with Generate, Regenerate, and authenticated Blob download. Tests: `tests/integration/test_applications_api.py::test_cover_letter_download_*`.

### BUG-031 — ✅ P3 — Missing pagination on applications and job listings (Task A5, B2)
- **Symptom:** Applications and job listings displayed unbounded lists without page controls, degrading UI performance on large datasets.
- **Root cause:** Frontend lacked pager components and didn't pass page/limit query parameters.
- **Fix:** Created reusable `Pager` component; wired pagination to `ApplicationsPage` and `JobSearchPage` with `keepPreviousData` and automatic page resets on tab changes. Tests: `frontend/src/__tests__/components/Pager.test.tsx`.

### BUG-032 — ✅ P2 — Missing account deletion workflow in frontend (Task A6)
- **Symptom:** Although `DELETE /api/v1/auth/account` existed on the backend, users had no UI option to delete their accounts in compliance with GDPR.
- **Root cause:** No frontend client or UI component for account deletion.
- **Fix:** Built `DeleteAccountCard` danger zone card in `SettingsPage`, requiring typed email confirmation to enable the delete action; displays 30-day grace period copy before permanent purge (no restore path); clears React Query and auth stores and redirects to `/login`. Tests: `frontend/src/__tests__/components/DeleteAccountCard.test.tsx`.

### BUG-033 — ✅ P3 — Deprecated PyPDF2 library and unused ML dependencies (Task B4)
- **Symptom:** Build times and dependencies were bloated by unused machine learning libraries (sentence-transformers, faiss-cpu, scikit-learn, numpy) and deprecated `PyPDF2`.
- **Root cause:** Legacy dependencies declared in `pyproject.toml` but unused across the codebase.
- **Fix:** Removed unused packages; migrated `core/documents/parser.py` and document tests to `pypdf>=4.0.0`. Tests: `tests/unit/test_document_parser.py`.

### BUG-034 — ✅ P2 — PII filter false positives on spaCy 3.8 and pricing bypass in LiteLLM >= 1.81 (Tasks C0, C4)
- **Symptom:** In spaCy 3.8, NER tagged "Easy Apply" as a `PERSON` entity, improperly blocking valid site skills at the PII filter. In LiteLLM >= 1.81, `cost_per_token` returned `(0.0, 0.0)` for unknown models instead of raising an error, defeating the local fallback price table and allowing unmetered spend.
- **Root cause:** Upstream library behavioral changes in newer minor versions.
- **Fix:** Pinned `spacy>=3.7.0,<3.8` and `litellm>=1.40.0,<1.81` in `pyproject.toml`; treated litellm 0.0 returns for non-zero tokens as unmapped to fall through to local fallback pricing. Tests: `tests/unit/test_llm_budget.py`.

### BUG-035 — ✅ P3 — Dead global `min_ats_score` configuration (Task W0-3)
- **Symptom:** `Settings.min_ats_score` existed in global configuration, conflicting with user-specific `UserSettings.min_ats_score`.
- **Root cause:** Redundant global setting left behind after per-user preference migration.
- **Fix:** Removed `min_ats_score` from global settings and schema; updated documentation to confirm ATS threshold is per-user. Tests: `tests/unit/test_settings.py`.

---

## Design-parity gaps vs `AutoApply AI.dc.html` (2026-07-13 audit)

Audited the frontend against all 24 sections of the design. The 12 product screens + command
palette + intervention modal + toasts + update-status dialog are all built. Newly added this pass
(ported faithfully, TDD): **404/403/500 system states** (`SystemStatePage` — 404 catch-all, 403 via
`RequireSuperuser` on `/admin`), **offline banner** (`OfflineBanner`, global), and the **"Reset your
password" screen** (`ForgotPasswordPage` at `/forgot-password`, linked from login — shipped as the
design's disabled "COMING SOON" stub). Remaining gaps, all **blocked on the un-built live-browser
backend spike**, not on frontend work:

### GAP-001 — 🔵 P3 — Live Apply "cockpit" view (design §LIVE APPLY COCKPIT)
- The design has a dedicated full cockpit: a live browser **viewport** streaming the agent's screen +
  a step ticker. We have the pieces it needs (dashboard live-now card, app-detail `RunTimeline`,
  intervention modal) but not the combined cockpit, because it renders **live browser screenshots**
  that only exist once `run_apply` streams them (the headful real-browser spike is still pending —
  see the phase-3 memory). Build the cockpit shell when that lands.

### GAP-002 — 🔵 P4 — Screenshot lightbox (design §SCREENSHOT LIGHTBOX)
- A fullscreen viewer for `Application.browser_screenshots`. Same dependency as GAP-001 — no
  screenshots are produced until the live-apply worker runs.

### GAP-003 — ✅ DONE (2026-07-13) — Job detail slide-in drawer (design §JOB DRAWER)
- Built `components/jobs/JobDrawer.tsx`: right-side drawer with match-score ring + skill/keyword
  sub-score bars, missing keywords, suggestions, description, "View posting", and **"Generate
  tailored résumé"**. Clicking a job title on `JobSearchPage` opens it and runs analyze. This also
  **wired the previously-orphaned `useGenerateResume`** action (résumé generate/tailor mount). TDD:
  `__tests__/components/JobDrawer.test.tsx` + a JobSearchPage integration test.

### GAP-005 — ✅ DONE (2026-07-13) — Résumé screen deeper parity (design §RÉSUMÉS)
- Rebuilt `ResumesPage` to the master-detail design: `ResumeCard` (thumbnail, base/tailored/optimized
  **type badges**, target-job subtitle, ATS, optimize + **authenticated-blob Download**) + upload
  dropzone + sticky `ResumePreviewPanel` (ATS ring + skill/keyword/experience/education sub-scores +
  **"Score vs job"** wiring `useScoreResume` with a job picker + PDF/DOCX download) + header
  **"Generate tailored"**. New `resumeService.downloadResumeFile` (bearer blob → object URL).
  TDD: 22 résumé tests. **Live-verified** (login → /resumes → select job → Score → real backend
  breakdown + success toast).
- **Adversarial multi-lens review** (5 lenses × find→verify workflow) found & I fixed: a **HIGH**
  correctness bug (a stale score bled onto the wrong résumé after the selection implicitly shifted —
  fixed with a `score.resume_id === resume.id` guard in the panel), card download hardcoding PDF
  (now picks an available format + disables when none), card subtitle showing template instead of the
  target job, name-scoped a11y labels on the optimize/download buttons + a labeled score-ring, the
  header subtitle copy, and added error/empty/stale-score test coverage.
- **Residual — updated 2026-07-23:** the two a11y nits are ✅ **fixed** (the generate buttons now
  use `aria-disabled` with accessible descriptions for the disabled reason, and the ResumeCard
  select label folds in the variant/type). The design's **before/after ATS delta pill** is
  ✅ **DONE**: `optimize_resume` persists the source résumé's pre-optimization score
  (`tests/unit/test_resume_service.py`), `ResumePreviewPanel` renders the pill for an optimized
  variant (`+N ATS after optimization · was X`, offer/rejected colors), and `ResumesPage` passes the
  base's stored score (`baseAtsScore`) — tests in `ResumePreviewPanel.test.tsx` + `ResumesPage.test.tsx`.
  `useScoreResume` is now wired (was orphaned).

### GAP-004 — ✅ DONE (2026-07-17) — Password-reset backend + wired frontend
- **Backend:** new `password_reset_tokens` table (migration `0006`), single-use hashed tokens, a
  pluggable **mailer** (`services/mailer.py` — `log` provider by default so it works in dev/CI with
  no mail server; `smtp` provider for real delivery), and endpoints `POST /auth/forgot-password`
  (uniform response → no account enumeration, also closes review item **L4**) + `POST
  /auth/reset-password` (redeem token → set password → revoke all refresh sessions). Service:
  `services/password_reset.py`. Tests: `tests/integration/test_password_reset.py`,
  `tests/unit/test_password_reset_service.py`, `tests/unit/test_mailer.py`.
- **Frontend:** `ForgotPasswordPage` rebuilt into a working form (submit → uniform "check your email"
  confirmation via the shared `AuthNotice` card); new `ResetPasswordPage` at `/reset-password?token=`
  (new + confirm password → success → sign-in link). `authService.forgotPassword/resetPassword`
  added; `api.ts` `isAuthEntry` now covers forgot/reset so their 401s don't trigger a refresh-retry.
  Tests: `__tests__/pages/ForgotPasswordPage.test.tsx`, `__tests__/pages/ResetPasswordPage.test.tsx`.
- **Left to you:** set `EMAIL__PROVIDER=smtp` + SMTP creds (see SETUP_AND_BREADCRUMBS) for real email
  delivery. Email *verification* on register is still deferred (separate product feature).

### GAP-006 — ✅ Backend DONE (2026-07-17) — Platform session import (assisted-login backbone)
- **What:** `run_apply` requires a saved platform session at prerequisite-check time, but there was
  **no write path** to create one. Added `POST/GET/DELETE /api/v1/platform-sessions`: import a captured
  Playwright `storage_state` (encrypted at rest via `CredentialStore` → `user_credentials`
  kind=`platform_cookies`), upsert the `platform_sessions` metadata row, list connected platforms
  (cookies never returned), and disconnect. Service: `services/platform_session.py`; schema validates
  the platform against `SUPPORTED_PLATFORMS` and requires a non-empty `cookies` list. Tests:
  `tests/integration/test_platform_sessions.py`.
- **Why it matters:** a technically-capable user (or the eventual headful assisted-login UX) can now
  provide a session so `run_apply` can proceed — this is the stable contract both capture paths write to.
- **Deliberately NOT built (needs your decision):** the user-facing "Connect LinkedIn/Indeed" UI + the
  headful in-browser capture flow, because that bakes in the automation/ToS posture that is yours to
  decide (SETUP_AND_BREADCRUMBS §4.1). The live capture + real run still need a headful browser host.

Not ported by design intent: **Style guide** (design-reference only) and **Roadmap** (the design
itself labels it "unbuilt").
