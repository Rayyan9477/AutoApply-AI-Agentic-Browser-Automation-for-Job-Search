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
- **Residual (deferred):** the design's **before/after ATS delta pill** needs a "previous score"
  the backend doesn't expose yet (Resume/ResumeScoreResponse carry no prior value) — blocked like the
  other backend-data gaps. Two low a11y nits left: the disabled "Generate tailored" reason lives only
  in `title` (kept native `disabled`), and the select-card button's aria-label doesn't fold in the
  type/template. `useScoreResume` is now wired (was orphaned).

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
