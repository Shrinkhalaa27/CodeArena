# Development

## Prerequisites
Git, Node.js 22 + npm, Python 3.12+, Docker (Compose v2). 8 GB RAM recommended; Judge0 needs more.

## Option A — everything in Docker
```bash
cp .env.example .env          # set JWT_SECRET:  openssl rand -hex 32
docker compose up -d --build                      # web, api, worker, postgres, redis
docker compose --profile judge up -d --build      # + self-hosted Judge0 CE (real sandbox)
```
Web http://localhost:3000 · API docs http://localhost:8000/docs · health `/health`, readiness `/ready`.
The API container runs migrations and the (idempotent) seed on start.
For Judge0, first `cp infra/judge0/judge0.conf.example infra/judge0/judge0.conf`, change the passwords,
and set the same token as `JUDGE0_AUTH_TOKEN` in `.env`. Without Judge0, set `JUDGE_BACKEND=fake` for UI work (see below).

## Option B — services on the host (fast iteration)
```bash
docker compose up -d postgres redis

cd services/api
python -m venv .venv && source .venv/bin/activate      # PowerShell: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
export DATABASE_URL=postgresql+psycopg://codearena:codearena@localhost:5432/codearena   # PowerShell: $env:DATABASE_URL="..."
export JWT_SECRET=dev-secret-dev-secret-dev-secret-0123456789
alembic upgrade head && python -m app.seed
uvicorn app.main:app --reload --port 8000
python -m app.workers.judge_worker                      # second terminal

cd apps/web && npm install && npm run dev               # third terminal
```
Demo accounts (development only): set `SEED_DEMO_USERS=true` before seeding →
`demo@codearena.dev / demo-password-1`, `setter@codearena.dev / setter-password-1`.
Admin: set `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD` before seeding. Never reuse these in production.

## The judge backends
| `JUDGE_BACKEND` | What it is | Allowed |
|---|---|---|
| `judge0` | Real sandboxed execution via Judge0 CE | everywhere |
| `fake` | Test double. Recognises marker comments (`@@WRONG`, `@@TLE`, `@@COMPILE_ERROR`, `@@RUNTIME_ERROR`, `@@INFRA`, `@@ECHO`). **Never runs submitted code.** | dev / test / CI only — refused when `APP_ENV=production` |

`QUEUE_BACKEND`: `redis` (default), `inline` (dev only; judges in a thread of the API process, no Redis needed), `memory` (tests).

## Tests and quality gates
```bash
cd services/api && ruff check app tests && ruff format --check app tests alembic && pytest -q
cd apps/web && npm run typecheck && npm run lint && npm test && npm run build
# E2E (needs API + worker + web running, JUDGE_BACKEND=fake or real Judge0):
cd apps/web && npx playwright install chromium && E2E_BASE_URL=http://localhost:3000 npx playwright test
#   use a pre-installed browser instead:  PW_CHROMIUM_PATH=/path/to/chrome
```

## Judge0 notes
Judge0 CE 1.13.x uses `isolate`, which needs `privileged` workers and **cgroup v1** on the host. On hosts that only
have cgroup v2 (recent Ubuntu/Debian, Docker Desktop) the workers fail to start; either boot with
`systemd.unified_cgroup_hierarchy=0` or use a Judge0 release/host that supports v2. Verify language ids against
`GET /languages` on your deployment (`app/services/judge.py` holds the id map). Before exposing the platform, run
fork-bomb, memory-bomb, infinite-loop, huge-output and network-access programs through it and confirm each is contained.

## Troubleshooting
- **DB connection refused** — check the Postgres container is healthy and `DATABASE_URL` host matches (`localhost` on host, `postgres` in Compose).
- **Submission stuck in QUEUED** — is the worker running? `redis-cli llen` the queue; check worker logs. Stale jobs are re-queued on worker start.
- **INTERNAL_ERROR / "Judge Error"** — infrastructure failure (Judge0 unreachable or unhealthy), not your code. Check `/api/v1/admin/judge-health`.
- **CORS error** — `WEB_ORIGIN` must equal the web origin exactly.
- **AI unavailable** — `LLM_PROVIDER` unset, key missing, quota hit (20/day default), or provider timeout. The platform works without it.
