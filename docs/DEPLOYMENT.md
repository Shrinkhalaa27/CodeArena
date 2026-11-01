# Deployment notes

Free tiers change; check each provider's current limits and terms before relying on them. Nothing below is guaranteed unlimited or permanent.

## Free-tier-friendly demo shape
| Component | Demo option | Caveat |
|---|---|---|
| Web (Next.js) | Vercel / Netlify / Cloudflare Pages / any container host | `NEXT_PUBLIC_API_URL` is baked at build time |
| API + worker | One small container host (Fly.io, Render, Railway…) | Free instances sleep; the worker needs an always-on process |
| PostgreSQL | Neon / Supabase free tier | Compute may sleep; storage is capped |
| Redis | Upstash or a small container | Request limits apply |
| Judge0 CE | **Self-hosted VM** with Docker, cgroup v1 | Not suitable for most free PaaS (needs privileged containers) |
| AI | Optional Gemini / Groq / OpenRouter key | Quotas and model availability change; platform works without it |

## Required for any public deployment
- `APP_ENV=production`; a random `JWT_SECRET` (32+ chars); `JUDGE_BACKEND=judge0`; `QUEUE_BACKEND=redis` (the app refuses to start otherwise).
- TLS in front of web and API; `WEB_ORIGIN` set to the exact public web origin.
- Judge0 on a private network, authenticated, never reachable from the internet; no outbound network for submissions.
- Run the sandbox threat tests (fork bomb, memory bomb, infinite loop, huge output, network access) first.
- Secrets from a secret manager, not committed `.env` files. No `NEXT_PUBLIC_` secrets.
- Backups for PostgreSQL; retention policy for source code and logs.

## What moves to paid / self-hosted under real traffic
Judge workers (CPU-bound, scale horizontally), PostgreSQL (connection limits, backups), Redis, and error/trace monitoring.
