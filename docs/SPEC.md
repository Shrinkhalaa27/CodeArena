# CodeArena — Product Requirements & Technical Specification

**Version:** 1.0  
**Status:** Implementation blueprint  
**Product type:** Full-stack competitive programming and contest platform

## 1. Vision

CodeArena is a web platform where developers practice algorithmic problems, submit code to a secure judge, participate in timed contests, compare performance, and learn from structured feedback. AI assistance is an optional learning feature, never part of the trusted judging path.

## 2. Goals and non-goals

### Goals
1. Deliver a complete problem-to-submission-to-verdict workflow.
2. Support private test cases and deterministic judging.
3. Support scheduled and live contests with a well-defined scoring policy.
4. Provide reliable user profiles, statistics, and rating history.
5. Offer optional AI hints and explanations with privacy controls.
6. Be deployable locally with Docker Compose and documented for production hardening.

### Non-goals for MVP
- Running arbitrary code directly in application servers.
- Supporting every programming language or multi-file project initially.
- Plagiarism detection as a definitive accusation mechanism.
- AI-generated verdicts or AI-based replacement of test-case judging.
- Payments, ads, social feeds, or mobile native applications.

## 3. Personas and roles

- **Visitor:** browse public problems, contests, and public profiles.
- **Registered user:** solve, submit, join contests, view history and ratings.
- **Problem setter:** create/edit problems, examples, constraints, and test data.
- **Contest admin:** schedule contests, register participants, monitor scoreboard, freeze/unfreeze scoreboard, finalize results.
- **Platform admin:** manage users, roles, abuse reports, system health, and audit logs.

Enforce role-based access control on the backend. Hiding UI controls is not authorization.

## 4. Core user journeys

### 4.1 Practice
1. User opens Problems.
2. Filters by difficulty, topic, tags, and status.
3. Opens a problem with statement, examples, constraints, and supported languages.
4. Writes code in Monaco; selects language.
5. Runs against sample/custom input.
6. Submits for hidden test evaluation.
7. Sees verdict, runtime, memory, and permitted feedback.
8. Reviews submission history and optionally asks AI for a hint/explanation.

### 4.2 Contest
1. User views upcoming/live/past contests.
2. Registers before start (if registration is enabled).
3. At start, contest problems and timer become available.
4. User submits solutions; contest submissions are tagged to that contest.
5. Scoreboard updates according to contest policy.
6. During freeze, public scoreboard hides configured recent details while admins retain full visibility.
7. On finish, final scoreboard and rating changes are published.

### 4.3 Problem authoring
1. Authorized setter creates a draft problem.
2. Adds statement, input/output format, constraints, examples, tags, difficulty, time/memory limits.
3. Uploads test cases and expected outputs, or configures a trusted generator workflow.
4. Runs validation against reference solution.
5. Publishes after admin review.
6. Hidden tests remain inaccessible to normal users and AI endpoints.

## 5. Functional requirements

### FR-01 Authentication and profile
- Email/password signup and login; OAuth may be added later.
- Secure password hashing (Argon2id preferred).
- Email verification and password reset flow.
- Session expiry, refresh rotation, logout, and account deletion.
- Profile: handle, avatar, bio, country/timezone (optional), joined date.
- Public stats: solved count by difficulty, accepted submissions, contests, rating graph, activity heatmap.
- Users can choose whether profile and activity are public.

### FR-02 Problem catalogue
- Search by title/ID; filter by difficulty, topic, tags, status.
- Pagination and stable sorting.
- Problem details: statement, examples, constraints, input/output, limits, hints (if released).
- Problem states: draft, review, published, archived.
- Store editorial/official solution separately with restricted access.

### FR-03 Code editor and run
- Monaco Editor with language selector, theme, font size, reset, copy, and keyboard shortcuts.
- Starter templates per language.
- Custom input execution is a run action and must be rate limited.
- Autosave drafts locally; server-side draft sync is optional.
- Accessible editor controls and responsive fallback.

### FR-04 Submission and judging
- Submission states: `QUEUED`, `COMPILING`, `RUNNING`, `ACCEPTED`, `WRONG_ANSWER`, `TIME_LIMIT_EXCEEDED`, `MEMORY_LIMIT_EXCEEDED`, `RUNTIME_ERROR`, `COMPILATION_ERROR`, `INTERNAL_ERROR`.
- Create submission returns immediately with submission ID and queued status.
- Worker evaluates each test case in isolation through Judge0 CE.
- Compare output using documented normalization (default: trim trailing whitespace per line and final newline; do not collapse meaningful internal whitespace unless problem config says so).
- Stop early on first failing test for standard judging; support full evaluation for score-based problems.
- Persist verdict, passed/total tests, execution metrics, timestamps, language, code snapshot, and contest association.
- Never return hidden input/expected output to participants.
- Rejudge support restricted to admins; preserve audit history.
- Idempotent worker processing and retry policy for infrastructure errors only.

### FR-05 Contest management
- Contest fields: title, slug, description, start/end UTC timestamps, registration window, visibility, rules, scoreboard freeze time, penalty policy, rating eligibility.
- Contest states: draft, scheduled, running, frozen, ended, cancelled.
- Problems assigned with labels and point values.
- Registration/unregistration rules.
- Server time is authoritative; client timer is display-only.
- Reject submissions outside contest window unless practice mode is explicitly selected.
- Scoreboard sorting and tie-breaking must be deterministic and documented.
- MVP scoring: 1 point per accepted problem; penalty = elapsed minutes at first accepted attempt + configurable penalty per wrong attempt before acceptance. Tie-break by total penalty, then earlier last accepted timestamp, then stable user ID.
- Keep practice and contest submissions separate in scoreboard calculations.

### FR-06 Leaderboards and rating
- Global, monthly, and contest leaderboards.
- Contest standings derived from accepted submissions and penalty policy.
- Rating history chart and rank percentile.
- Use a documented rating algorithm (e.g. Elo-like or Codeforces-inspired variant) only after enough contest data exists. Clearly label provisional ratings.
- Recompute via idempotent background job; retain rating-change records.

### FR-07 AI learning assistant (optional)
- Explain concepts, provide progressive hints, explain a user's own code, identify likely edge cases, and create a personalized practice plan.
- User must explicitly invoke AI; no automatic code upload.
- Context may include public problem statement and user-selected code only.
- Never include hidden tests, expected outputs, official private editorial, other users' submissions, secrets, or admin content.
- AI output is advisory and may be wrong. It cannot set verdicts, scores, or ratings.
- Apply per-user quotas, prompt-size limits, abuse controls, and provider timeout handling.
- If no provider key is configured, hide or disable AI actions gracefully.

### FR-08 Admin and moderation
- Manage roles, users, problems, contests, tags, languages, and announcements.
- Review problem/test-case changes.
- View judge queue health and failed jobs.
- Audit sensitive actions: role changes, problem publication, rejudge, contest edits, score overrides.
- No direct editing of user verdicts without an auditable admin action.

### FR-09 Notifications
- In-app notifications for accepted submissions, contest reminders, contest start/end, and rating updates.
- Email is optional and must be opt-in.
- Avoid sending secrets or source code in email.

## 6. Non-functional requirements

- **Security:** sandbox untrusted code; strict authorization; input validation; CSRF protections where cookie auth is used; secure headers; rate limits; secrets management; audit logging.
- **Reliability:** submission creation is durable before acknowledging; queue retries are bounded; failed jobs are observable; no duplicate scoreboard points.
- **Performance targets (initial):** normal API p95 under 500 ms excluding judge execution; problem list under 1 s at demo scale; scoreboard refresh under 2 s at demo scale.
- **Scalability:** API stateless; judge workers horizontally scalable; Redis queue; database indexes on common filters.
- **Accessibility:** keyboard navigation, contrast, semantic labels, reduced motion, responsive layouts.
- **Maintainability:** typed contracts, migrations, linting, tests, structured logs, clear module boundaries.
- **Privacy:** collect minimal profile data; provide account deletion/export path; set retention policy for source code and logs.
- **Observability:** correlation/request IDs, queue depth, judge latency, error rate, AI token usage, and database health.

## 7. MVP acceptance criteria

A release is not MVP-complete until all are true:
1. A user can register, log in, and update a profile.
2. Public problem list and problem detail pages load from the database.
3. User can run sample/custom input and submit code.
4. A sandboxed judge returns at least Accepted, Wrong Answer, Compilation Error, Runtime Error, and Time Limit Exceeded.
5. Hidden tests are never exposed through public API or client bundle.
6. Submission status is updated asynchronously and persisted.
7. Contest admin can create a contest and attach problems.
8. Registered user can submit during contest; scoreboard reflects accepted solutions and penalties.
9. Unit, API integration, and core Playwright E2E tests pass.
10. Docker Compose setup works from a clean clone using documented steps.
11. No API secrets are committed; `.env.example` contains placeholders only.
12. README includes architecture, setup, seed/demo credentials policy, troubleshooting, screenshots, and limitations.

## 8. Suggested UI routes

- `/` landing page
- `/problems` problem catalogue
- `/problems/[slug]` problem + editor workspace
- `/submissions/[id]` submission detail
- `/contests` contest catalogue
- `/contests/[slug]` contest overview
- `/contests/[slug]/problems/[problemSlug]` contest workspace
- `/contests/[slug]/leaderboard` scoreboard
- `/leaderboard` global rankings
- `/profile/[handle]` public profile
- `/dashboard` personal dashboard
- `/settings` account preferences
- `/admin` admin dashboard
- `/admin/problems`, `/admin/contests`, `/admin/judge`

## 9. Design direction

- Distinctive dark-first developer interface with optional light mode.
- Deep navy/charcoal base, restrained violet/cyan accent, readable contrast.
- Dense but breathable data tables; avoid excessive glassmorphism.
- Use consistent spacing, typography scale, skeleton states, empty states, loading states, error states, and toast feedback.
- Problem workspace: statement panel + editor panel + bottom console/results panel; resizable split panes on desktop.
- Mobile: statement and editor become tabs; editor controls remain reachable.
- Landing page should show a clear CTA, featured problems, active/upcoming contests, and platform stats.
- Include polished charts: rating history, activity heatmap, language distribution, solved-by-difficulty.

## 10. Risks and mitigations

- **Arbitrary code execution:** delegate to sandboxed Judge0; never DIY with subprocess in API.
- **Judge endpoint quotas/outage:** self-host judge; queue submissions; expose retryable infrastructure status.
- **Hidden-test leakage:** separate private test storage and authorization paths; redact logs and AI context.
- **Scoreboard race conditions:** transactionally persist accepted result and recompute idempotently.
- **AI hallucination:** label as assistance; never use AI for evaluation.
- **Free-tier changes:** local Docker path must remain functional; document hosted providers as optional.
