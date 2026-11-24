# Codebase Review — Bugs & Issues (2026-07-06)

Whole-system review of AutoApply AI (backend, frontend, structure, deploy). Baseline was
**green** before this review — backend 606 tests pass, frontend 71 pass, ruff + tsc clean —
so every item below is a defect the test suite does **not** catch (untested branches, gated
browser paths, deploy-only wiring, concurrency, or design gaps).

Method: a 10-dimension reviewer fan-out (documents / auth-security / harness / ATS / platforms
/ LLM / tenant-data / api-services / frontend / structure), with **every reported finding
re-verified by reading the actual code** at the cited `file:line`. Findings that turned out to
be already-handled are listed at the bottom so they are not re-investigated.

Legend — **Status:** `confirmed` (verified against current code) · `browser-path` (only manifests
once the real browser-use apply/scrape spike is enabled — the documented remaining work) ·
`needs-live-check` (mechanism verified, real-world trigger depends on an external lib's runtime type).

---

## ✅ Remediation status (2026-07-06) — ALL confirmed items fixed

Every finding below has been fixed and covered by a regression test, in five groups, keeping the
suite green throughout. Final gate: **backend 630 passed** / 1 skip / 1 xfail, ruff clean, mypy
clean on touched files; **frontend 74 passed**, tsc + lint clean. No schema change → no migration.
Nothing committed (staged for review).

- **H1** templates now `COPY`'d into both prod images + a guard test asserting every
  `RESUME_TEMPLATES` entry exists on disk.
- **H2** API image runs uvicorn with `--proxy-headers --forwarded-allow-ips=*` (safe: `expose`-only).
- **H3** `search_jobs` dedups in memory via a pre-fetched key set + derives a stable URL-hash id
  for blank-id listings (this also fixed a *deeper* bug the test surfaced — blank ids collided on
  the `(user, platform, platform_job_id)` unique index and failed the whole commit).
- **M1** WS subscriber now writes through `ConnectionManager.send_raw` (per-socket lock).
- **M2/M3** anomaly detector upserts one open issue per category + windows the failure rate to 6h.
- **M4** cover-letter content is `<p>`-wrapped (escaped) so paragraphs survive.
- **M5** frontend `api.ts` does a single-flight refresh-and-retry on 401.
- **M6** platform parsers coerce the browser-use `AgentHistoryList` to a list defensively.
- **M7** spaCy model cached (`core/ats/nlp.get_nlp`) + scoring offloaded via `run_in_executor`.
- **L1** review job re-raises transient LLM errors so Arq retries. **L2** resume PDF autoescape on.
  **L3** dropped the inert (and per-pair-expensive) semantic branch in `SkillMatcher` — exact+fuzzy
  only. **L5** register maps a race unique-violation to 409. **L6** identical distilled skills are
  deduped by content (distinct skills still coexist). **L7** PII gate adds NER full-name + street
  -address rejection. **L8** loop detection keys on a composite (url+action+next_goal) step key.
- **L4** left as a documented product tradeoff (see its entry); now mitigated by the H2 fix.
- **Related, intentionally left:** `keyword_analyzer._semantic_similarity` has the same
  vectors-model dependency as L3 but is *tested with a vectors mock* and blended into the keyword
  score — it degrades gracefully with `en_core_web_sm` and works if a `md`/`lg` model is installed,
  so it was kept. **S1** (300-line files) is a refactor, deferred.

---

## MVP triage (what blocks a working product)

The MVP is the end-to-end product in **placeholder-apply mode**: register → search (Exa) →
upload/generate/score resume → create/approve/track applications → dashboards, with live WS
updates. Ordered for that goal:

| Tier | Items | Why |
|------|-------|-----|
| **MVP blockers** | H1, H2, M4, M5, M7 | Resume generation dead in prod (H1); prod auth lockout (H2); broken cover-letter layout (M4); users logged out every 15 min (M5); resume scoring blocks the event loop (M7). |
| **MVP reliability** | M1, M2, M3, L1, L2, L5 | WS frame corruption; admin health flood/wrong-signal; harness silently drops feedback; garbled resume fields; register 500 on dup. |
| **Deferred w/ browser spike** | H3, M6, L8 | Browser-scrape job discovery isn't viable on a request anyway (30s+ per run); **Exa is the MVP discovery path**. Fix alongside the live-browser work. |
| **Polish / decide** | L3, L4, L6, L7, S1 | Semantic match inert (install `md` model or drop); enumeration tradeoff; harness skill hygiene; 300-line refactor. |

---

## HIGH

### H1 — Production Docker images never copy `templates/`; resume generation fails in prod · `confirmed`
- **Where:** [docker/Dockerfile.api](../docker/Dockerfile.api) & [docker/Dockerfile.worker](../docker/Dockerfile.worker) (only `COPY backend/app/ ./app/` + `pyproject.toml`); consumed by [generator.py:69](../backend/app/core/documents/generator.py#L69) (`templates_dir: Path = Path("templates")`) and [pdf_renderer.py:99](../backend/app/core/documents/pdf_renderer.py#L99).
- **Problem:** The Jinja/WeasyPrint templates live at the **repo root** `templates/` (resume + cover_letter), but neither Dockerfile copies that directory into the image, and `DocumentGenerator` is always constructed with the default **relative** `Path("templates")` (resolved against the container CWD `/app`, where it does not exist). See [resume.py:364](../backend/app/services/resume.py#L364)/[:652](../backend/app/services/resume.py#L652) — both use defaults.
- **Failure:** In the prod images, any resume generate/optimize call raises `TemplateError("Template directory not found at templates/resume/modern")`; cover-letter falls back to unstyled inline HTML. Not caught by tests because doc-gen tests **mock** `DocumentGenerator` ([test_cover_letter_service.py:50](../backend/tests/unit/test_cover_letter_service.py#L50)).
- **Fix:** Add `COPY templates/ ./templates/` to both Dockerfiles (build context is repo root, so the dir is available), or point `DocumentGenerator` at a settings-resolved absolute templates path.

### H2 — Rate limiter collapses all clients into one bucket behind Caddy · `confirmed`
- **Where:** [ratelimit.py:39](../backend/app/core/ratelimit.py#L39) (`client = request.client.host`), [auth.py:34](../backend/app/api/v1/auth.py#L34) (`rate_limit(5, 60)` on `/login` + `/register`), [Dockerfile.api:26](../docker/Dockerfile.api#L26) (uvicorn CMD has **no** `--proxy-headers`).
- **Problem:** In prod, Caddy reverse-proxies to `api:8000`. Uvicorn without `--proxy-headers` sets `request.client` to the **TCP peer = the Caddy container**, so `request.client.host` is one fixed internal IP for every external request. The rate-limit key `f"{client}:{path}"` is therefore identical for all users.
- **Failure:** The `5 requests / 60s` auth throttle becomes a **global** counter — 5 login attempts anywhere lock out *every* user for the rest of the window (trivial auth DoS), and per-attacker brute-force isolation is lost.
- **Fix:** Start uvicorn with `--proxy-headers --forwarded-allow-ips="*"` (safe here — `docker-compose.prod.yml` uses `expose`, not `ports`, so only Caddy can reach uvicorn and clients cannot spoof `X-Forwarded-For`). Caddy already sets XFF, so `request.client.host` will then be the real client IP.

### H3 — `search_jobs` dedup loop collapses distinct scraped jobs & re-appends duplicates · `browser-path`
- **Where:** [job_search.py:103-128](../backend/app/services/job_search.py#L103-L128) (and the Exa branch [:143-157](../backend/app/services/job_search.py#L143-L157)).
- **Problem:** The loop issues a per-listing `SELECT` to check for an existing job. The session uses the default `autoflush=True`, so that SELECT **flushes the pending `db.add(job)` from the previous iteration**. When multiple listings share a `platform_job_id` — including the common case where the parser sets `platform_job_id=str(item.get("id",""))` and the browser agent returned **no id** (all `""`) — the first row is flushed, the next SELECT matches it, and every subsequent listing appends that same row.
- **Failure:** N distinct jobs → 1 persisted, N-1 silently discarded, and the response returns N identical items with an inflated `total`. Even with non-empty ids, two same-id listings in one page append the existing row twice.
- **Fix:** Pre-fetch existing keys in one query into a `set`, dedup **within the batch** with a `seen` set, and treat an empty `platform_job_id` as non-dedupable (derive a stable key from the listing URL when the id is blank). This also removes the N+1 (see L-N1).

---

## MEDIUM

### M1 — WebSocket subscriber bypasses the per-socket send lock · `confirmed`
- **Where:** [subscriber.py:31](../backend/app/api/websocket/subscriber.py#L31) (`await ws.send_text(text)`); the lock it should use is [events.py:49-56](../backend/app/api/websocket/events.py#L49-L56); the ping/pong path *does* use it via [endpoint.py:56](../backend/app/api/websocket/endpoint.py#L56).
- **Problem:** `ConnectionManager` created a per-socket `asyncio.Lock` whose stated purpose is "the pub/sub subscriber task and the ping/pong handler never call `send_text` concurrently." The ping/pong path honors it (`manager.send_to → _send`), but the subscriber — the very task the lock names — calls `ws.send_text` directly.
- **Failure:** A forwarded progress event and a concurrent `pong` can interleave two sends on one socket → corrupted frames or Starlette's "Concurrent call to send()" `RuntimeError`, dropping the connection.
- **Fix:** Add a locked `ConnectionManager.send_raw(ws, text)` (acquire `self._locks[ws]` then `send_text`) and call it from `forward_user_events` instead of `ws.send_text`.

### M2 — Anomaly detector re-inserts duplicate `SystemIssue` rows every tick · `confirmed`
- **Where:** [anomaly.py:83-89](../backend/app/core/harness/anomaly.py#L83-L89); scheduled 4×/hour by [tasks.py:339](../backend/app/workers/tasks.py#L339).
- **Problem:** `detect_anomalies` unconditionally inserts a new `SystemIssue` whenever a condition holds — no check for an existing open issue of the same category, and nothing ever sets `status="resolved"`.
- **Failure:** A single ongoing condition (e.g. failure-rate ≥ 0.5) inserts a fresh `critical` row every 15 min → ~96 identical rows/day, unbounded table growth, and the admin health view floods with duplicates.
- **Fix:** Before inserting, look up an open issue of the same category; if present, update `detected_at`/`signals` (or skip within a cooldown) instead of inserting. Optionally auto-resolve when the condition clears.

### M3 — "Recent" failure-rate anomaly actually measures all-time rate · `confirmed`
- **Where:** [anomaly.py:48-61](../backend/app/core/harness/anomaly.py#L48-L61).
- **Problem:** The comment says "High **recent** application-failure rate," but both `count()` queries have **no time filter** — they count every application ever created.
- **Failure:** (1) A mature deployment with a low lifetime failure rate never fires the alert even during a 100%-failing hour (historical denominator dominates). (2) A young deployment with a few early failures is pinned to a permanent `critical` even after it recovers.
- **Fix:** Add a recency window to both counts, e.g. `.where(Application.created_at >= now - timedelta(hours=6))`, keeping `MIN_SAMPLE` on the windowed count.

### M4 — Cover-letter PDF collapses all paragraphs into one block · `confirmed`
- **Where:** [generator.py:362-367](../backend/app/core/documents/generator.py#L362-L367) + template [templates/cover_letter/standard/template.html:21-23](../templates/cover_letter/standard/template.html#L21-L23) (`<div class="body">{{ content }}</div>`).
- **Problem:** LLM cover-letter content is plain prose with `\n\n` paragraph breaks. The template renders it with `autoescape` on and **no `<p>` wrapping** and the CSS has no `white-space: pre-line`, so HTML whitespace-collapsing merges the whole letter into one run-on paragraph. The DOCX renderer splits on `\n\n` correctly → the two formats are inconsistent, and the PDF (the default) is visibly broken.
- **Fix:** Convert content to paragraphs before rendering (`{% for p in paragraphs %}<p>{{ p }}</p>{% endfor %}`) or inject `_text_to_html(content)` via a `|safe` variable, or add `white-space: pre-line;` to `.body` in each cover-letter `style.css`.

### M5 — Frontend never refreshes the access token on 401 (logs users out every 15 min) · `confirmed`
- **Where:** [frontend/src/services/api.ts:31-55](../frontend/src/services/api.ts#L31-L55) (response interceptor only calls `clear()` on 401). Stale comment claims "single-flight refresh … lands in Phase 1."
- **Problem:** The backend `/auth/refresh` is fully implemented and boot-time silent refresh works ([AuthProvider.tsx:20](../frontend/src/context/AuthProvider.tsx#L20)), but mid-session the 15-minute access token expiry triggers a 401 that just de-authenticates instead of transparently refreshing against the valid 30-day refresh cookie.
- **Failure:** Any active user is kicked to `/login` every ~15 minutes even though their session is still valid.
- **Fix:** Add a single-flight refresh interceptor: on a non-auth-entry 401, call `authService.refresh()` once (dedup concurrent 401s on one in-flight promise), update the store token, and retry the original request; only `clear()` if the refresh itself fails. *(Frontend is user-owned — flagged for their pass.)*

### M6 — Platform search parser can never match the real browser-use return type · `browser-path` `needs-live-check`
- **Where:** `_parse_search_results` in [linkedin.py](../backend/app/core/automation/platforms/linkedin.py)/[indeed.py](../backend/app/core/automation/platforms/indeed.py)/[glassdoor.py](../backend/app/core/automation/platforms/glassdoor.py) (`if isinstance(raw_result, list):`).
- **Problem:** On the search path no `output_model` is passed, so `BrowserAgent.run()` returns browser-use's raw `Agent.run()` value — an `AgentHistoryList` in 0.11.x, **not** a `list`. The `isinstance(..., list)` guard is then always False → `[]`. Tests pass only because they mock `platform.search` to return `list[JobListing]` directly.
- **Failure:** Every real (non-mocked) platform scrape yields zero jobs even when the agent extracted a valid array. Note `search_jobs` calls `platform.search()` **unconditionally** ([job_search.py:83](../backend/app/services/job_search.py#L83) — *not* gated by `BROWSER__LIVE_APPLY`), but a live browser run per search request is impractical regardless (30s+), so the **Exa branch is the intended MVP discovery path** and the browser-scrape platforms belong with the deferred live-browser spike.
- **Fix:** Extract the agent's final structured payload explicitly (`result.final_result()` / extracted-content JSON) and `json.loads` it into a list before parsing. Part of the documented real-browser spike; verify against the pinned browser-use version.

### M7 — Resume scoring reloads the spaCy model per request and blocks the event loop · `confirmed`
- **Where:** [resume.py:470](../backend/app/services/resume.py#L470) (`nlp = spacy.load("en_core_web_sm")`), also [:84](../backend/app/services/resume.py#L84) and [:613](../backend/app/services/resume.py#L613). `score_resume` (async) calls the **sync** `_score_with_full_engine` directly ([resume.py:442](../backend/app/services/resume.py#L442)) — no `run_in_executor`.
- **Problem:** Every resume score / upload skill-extraction / optimize call `spacy.load()`s the model **fresh from disk** (no module-level cache or `lru_cache`), and the whole synchronous scoring pipeline runs inline on the event loop.
- **Failure:** Each scoring request stalls (~0.5–1s model load + processing) and, because it isn't offloaded, **blocks the entire async server** for that duration — under any concurrency the API freezes per score. Also multiplies memory churn.
- **Fix:** Load the model once behind a cached accessor (`@lru_cache` / module singleton) shared by all three call sites, and offload `_score_with_full_engine` via `loop.run_in_executor(...)` (mirroring `pdf_renderer.render`). The same cached `nlp` also fixes L3 if upgraded to a vectors model.

---

## LOW

- **L1 — `review_application_run` swallows all exceptions** · `confirmed` — [tasks.py:274-275](../backend/app/workers/tasks.py#L274-L275). The whole review body is under `except Exception: logger.error(...)` and returns normally, so a transient provider 429/timeout in `judge`/`distil` makes Arq consider the job succeeded (no retry) and the run's verdict + skill-feedback are silently dropped. Fix: let transient errors propagate (Arq retries via `max_tries`) or record a placeholder verdict.
- **L2 — Resume PDF Jinja `Environment` has no autoescape** · `confirmed` — [pdf_renderer.py:113](../backend/app/core/documents/pdf_renderer.py#L113). Resume fields containing `<`, `>`, `&` are injected raw; WeasyPrint's parser treats `<…>` as tags and drops the content (e.g. "latency <5ms" loses "5ms"). Fix: `Environment(..., autoescape=select_autoescape(["html","xml"]))` to match the cover-letter path.
- **L3 — Skill-matcher semantic similarity is inert with the installed model** · `confirmed` — [skill_matcher.py:241-247](../backend/app/core/ats/skill_matcher.py#L241-L247). Both Dockerfiles install `en_core_web_sm`, which ships **no** word vectors, so `has_vector` is False → `_calculate_semantic_similarity` always returns 0.0. Skill matching silently degrades to exact + fuzzy only; the whole semantic dimension is dead weight. Fix: install `en_core_web_md`/`_lg` if semantic matching is intended, or drop the branch and document exact+fuzzy as the design.
- **L4 — Register endpoint enables account enumeration** · `confirmed` — [auth.py:85-87](../backend/app/api/v1/auth.py#L85-L87). Login is deliberately uniform (DUMMY_HASH), but `/register` returns a distinguishable `409 "Email already registered"` vs `201`, so an attacker can probe which emails have accounts. Fix: uniform response + email-verification, or accept the tradeoff explicitly (and fix H2 so the throttle actually isolates attackers).
- **L5 — Register check-then-insert race** · `confirmed` — [auth.py:85-94](../backend/app/api/v1/auth.py#L85-L94). Two concurrent registrations for the same email both pass the `existing is None` check; the second insert raises a DB `IntegrityError` that is **not** caught (the caught `IntegrityError` is the app one), surfacing as a 500 instead of a clean 409. Fix: catch `sqlalchemy.exc.IntegrityError` and map to 409.
- **L6 — Distilled domain skills grow without supersession** · `confirmed` — [skills.py:39-78](../backend/app/core/harness/skills.py#L39-L78). `record_skill` inserts a new version after every completed run and never retires prior active versions; `load_skills` returns the top-5 by score, which may be stale/superseded versions injected into the prompt. Fix: retire prior active versions on insert, or cap/dedup active versions per domain.
- **L7 — Cross-tenant skill PII gate is regex-only** · `confirmed` — [skills.py:27-36](../backend/app/core/harness/skills.py#L27-L36). `DomainSkill` is global (not tenant-scoped) and injected into every user's prompt; `pii_clean` only catches email/phone/key shapes, so a personal name, street address, or free-text eligibility answer distilled from a run summary can pass into a globally-shared skill. Fix: strengthen the gate (NER or a strict selector/URL allowlist), and/or scope distilled skills per-tenant.
- **L8 — URL-only loop detection misfires on modal apply forms** · `browser-path` — [observe.py:39-44](../backend/app/core/automation/runtime/observe.py#L39-L44). `_detect_loop` returns True on 3 identical trailing URLs; LinkedIn Easy Apply and other SPA/modal forms keep the same URL across steps, so a normal multi-step fill reads as a loop → `diagnose()` returns `LOOP` (checked before `FIELD_MISSING`) and applies spurious skill penalties. Fix: key the loop check on a composite (url+action+next_goal) or an explicit no-progress signal.
- **L-N1 — N+1 query in `search_jobs` dedup** · `browser-path` — [job_search.py:107-113](../backend/app/services/job_search.py#L107-L113) issues one SELECT per listing (~70 round-trips per search). Folded into the H3 fix (pre-fetch keys once).

---

## STRUCTURAL / CONVENTION

- **S1 — Files over the 300-line `CLAUDE.md` cap:** `services/resume.py` **696** (2.3×), `services/job_search.py` 441, `core/documents/generator.py` 392, `core/llm/client.py` 384, `workers/tasks.py` 346, `platforms/glassdoor.py` 345, `platforms/linkedin.py` 340, `platforms/indeed.py` 335. Maintainability only; `resume.py` is the clearest split candidate (parse / score / generate).

---

## Verified already-correct (checked, no action needed)

These were plausible concerns that the code already handles — listed so they aren't re-opened:
login timing side-channel (DUMMY_HASH always runs — [auth.py:110](../backend/app/api/v1/auth.py#L110)); refresh-token TOCTOU (atomic conditional `UPDATE … WHERE used=false` — [auth.py:148-156](../backend/app/api/v1/auth.py#L148-L156)); refresh cookie `Secure` in staging ([auth.py:45](../backend/app/api/v1/auth.py#L45)); LLM `completion_cost` crash guarded → cost 0.0 ([client.py:186-193](../backend/app/core/llm/client.py#L186-L193)); LLM fallback catch-all so non-`APIError` provider errors don't escape ([client.py:269-282](../backend/app/core/llm/client.py#L269-L282)); analytics timeline day-truncation in SQL ([analytics.py:185-195](../backend/app/services/analytics.py#L185-L195)); cross-tenant FK checks on create ([application.py:40-70](../backend/app/services/application.py#L40-L70)); `bulk_approve` state guard ([dispatch.py:80-89](../backend/app/services/dispatch.py#L80-L89)); idempotent create dedup via SAVEPOINT ([application.py:79-99](../backend/app/services/application.py#L79-L99)); `record_skill` version-race retry ([skills.py:53-73](../backend/app/core/harness/skills.py#L53-L73)); approve route enqueues ([applications.py:113](../backend/app/api/v1/applications.py#L113)); worker stuck-`APPLYING` handling + timeout `CancelledError` branch ([tasks.py:191-214](../backend/app/workers/tasks.py#L191-L214)); tenant filter covers relationship/lazy loads ([tenant.py:33-51](../backend/app/db/tenant.py#L33-L51)).

---

## Suggested fix order

1. **H1, H2** — one-line deploy fixes, high impact, zero logic risk (templates COPY; uvicorn `--proxy-headers`).
2. **M1, M2, M3, M4, L1, L2, L5** — contained backend fixes, each with a regression test; keep the suite green.
3. **H3 / L-N1, L3, L4, L6, L7, L8, M6** — larger or browser-path changes; sequence with the real-browser spike.
4. **M5** — frontend refresh interceptor (user-owned frontend pass).
5. **S1** — optional refactor for the 300-line convention.
