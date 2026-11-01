# Data Model Notes

## Core relationships

```mermaid
erDiagram
  USERS ||--o{ SUBMISSIONS : creates
  USERS ||--o{ CONTEST_REGISTRATIONS : joins
  USERS ||--o{ RATING_HISTORY : earns
  PROBLEMS ||--o{ TEST_CASES : contains
  PROBLEMS ||--o{ SUBMISSIONS : receives
  PROBLEMS }o--o{ TAGS : categorized_by
  CONTESTS }o--o{ PROBLEMS : includes
  CONTESTS ||--o{ CONTEST_REGISTRATIONS : has
  CONTESTS ||--o{ SUBMISSIONS : receives
  SUBMISSIONS ||--o{ SUBMISSION_RESULTS : evaluated_as
```

## Important constraints

- `users.handle` unique, case-insensitive.
- `users.email` unique, normalized.
- `problems.slug` unique.
- `contest_registrations` unique on `(contest_id, user_id)`.
- `submission_results` unique on `(submission_id, test_case_id)`.
- A submission's `contest_id`, if present, must refer to a contest containing that problem.
- Published problem test cases are immutable to ordinary users.
- Store test-case visibility as server-side metadata; never serialize hidden case payloads to public schemas.
- Use database transactions for final verdict persistence and contest-score updates.
