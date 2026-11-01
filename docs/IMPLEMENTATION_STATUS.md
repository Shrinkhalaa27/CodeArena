# Implementation status

Legend: ✅ done and verified · 🟡 done, partly verified · ⬜ not implemented

## Verified in this repo (what was actually run)
- ✅ Backend: **39 pytest tests pass**; Ruff lint and format clean.
- ✅ Alembic migration applies to a fresh PostgreSQL 16; seed runs twice with no duplicates (11 problems, 2 contests).
- ✅ Frontend: TypeScript strict typecheck, ESLint, **14 Vitest tests**, and `next build` all pass.
- ✅ Playwright smoke test (register → open problem → submit → verdict) passes against real PostgreSQL + Redis + the worker process.
- 🟡 **Judge0 was not run.** The sandbox used for development has no Docker daemon, so the E2E test used the built-in
  fake judge (a test double that never executes code). The Judge0 adapter is covered by a mock-transport test only.
  The Docker images and `compose.yaml` were syntax-validated (`docker compose config`) but not built or started.
  Run the manual checklist in `docs/DEVELOPMENT.md` against real Judge0 before trusting it.
- ⬜ GitHub Actions workflow is written but has not been executed.

## Features
| Area | Status | Notes |
|---|---|---|
| Auth: register/login, Argon2id, JWT access + rotating refresh tokens, profile edit, privacy flag | ✅ | Rate-limited |
| Email verification, password reset, account deletion/export | ⬜ | Roadmap |
| Problem catalogue: search, filters, sort, pagination, tags, per-user solved/attempted | ✅ | 11 seeded problems |
| Hidden tests never in public schemas; unpublished = 404 | ✅ | Security tests |
| Problem workspace: Monaco (bundled locally), languages, custom-input Run, Submit, verdict, history | ✅ | Python, C++, Java, JavaScript |
| Submission pipeline: queued → worker → per-case results → transactional verdict; idempotency key; retries for infra errors only | ✅ | Judge0 path unverified (see above) |
| Verdicts: Accepted, WA, TLE, MLE, RE, CE, Internal Error | ✅ | Unit-tested mapping |
| Contests: registration, server-time window, freeze, penalties, deterministic tie-break, admin full view | ✅ | |
| Ratings: Elo-style, provisional label, idempotent finalize | ✅ | |
| Leaderboard, profiles (rating chart, heatmap, solved by difficulty, languages) | ✅ | |
| Admin: create/publish problems & contests, judge health, rejudge, audit log | 🟡 | No edit/delete UI; no role-management endpoint |
| AI assistant: hint + explain, quotas, provider adapters (Gemini/Groq/OpenRouter), off by default | 🟡 | Tested with a stub provider only; complexity/edge-case/practice-plan not built |
| Realtime | 🟡 | API exposes `/ws/submissions/{id}`; the web UI **polls** instead of using it |
| Dark/light theme, responsive layout, skeleton/empty/error states, accessible controls | ✅ | |
| Notifications, announcements, plagiarism tooling | ⬜ | Out of MVP scope |

## Deviations from the blueprint
- Next.js UI uses Tailwind and hand-written components rather than shadcn/ui.
- Queue is a small Redis list queue with an ack/requeue sweep rather than Celery/ARQ (one fewer moving part).
- Auth tokens are kept in `localStorage` (XSS-exposed). Moving the refresh token to an HttpOnly cookie is the top hardening item.
- Custom-input **Run** calls the Judge0 adapter from the API request (bounded, rate-limited); only **Submit** goes through the queue.

## Known limitations
No observability stack yet (structured logs and request ids only), no load testing, no backups/retention policy,
no sandbox threat-testing results. See `docs/ROADMAP.md` Phase 5.
