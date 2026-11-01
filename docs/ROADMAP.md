# Delivery Roadmap

## Phase 0 — Foundation
- Monorepo structure, formatting, linting, typed environment config.
- Compose PostgreSQL + Redis.
- FastAPI health endpoint, migrations, Next.js shell.
- CI: lint, typecheck, unit tests.

## Phase 1 — Core practice MVP
- Auth and profiles.
- Problem catalogue, problem detail, tags and difficulty.
- Monaco editor, language templates, custom input run.
- Judge0 integration, queue worker, verdicts and submission history.
- Seeded problems and automated tests.

## Phase 2 — Contests
- Contest creation and registration.
- Start/end enforcement using server time.
- Contest submissions and penalty calculations.
- Live scoreboard, freeze, final standings.
- Contest admin tools.

## Phase 3 — Community and analytics
- Global leaderboard and rating history.
- User activity calendar and statistics.
- Notifications, announcements, search improvements.
- Problem authoring workflow and admin audit logs.

## Phase 4 — AI learning assistant
- Provider adapter and optional Gemini/Groq/OpenRouter integration.
- Hint ladder, code explanation, complexity coach.
- Per-user quotas, privacy controls, safety tests.
- AI off switch and graceful no-key experience.

## Phase 5 — Production hardening
- Security review and sandbox threat testing.
- Load tests for submissions and scoreboard.
- Backups, monitoring, alerting, retention policy.
- Deployment manifests, domain, HTTPS, secret management.
- Accessibility and mobile QA.

## Definition of done for every phase
- Acceptance criteria written and tested.
- No fake data in production flows.
- Loading, empty, error, and success states implemented.
- API authorization tested.
- README and architecture docs updated.
