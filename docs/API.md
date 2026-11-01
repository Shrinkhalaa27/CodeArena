# API Contract Notes

Base path: `/api/v1`. JSON by default. Timestamps are ISO-8601 UTC. Use consistent error envelopes.

## Submission create request

```json
{
  "problem_id": "uuid",
  "language": "python",
  "source_code": "print(input())",
  "contest_id": null
}
```

Response: `202 Accepted`

```json
{
  "submission_id": "uuid",
  "status": "QUEUED",
  "created_at": "2026-01-01T10:00:00Z",
  "status_url": "/api/v1/submissions/uuid"
}
```

## Submission response

```json
{
  "id": "uuid",
  "status": "WRONG_ANSWER",
  "language": "python",
  "passed_tests": 3,
  "total_tests": 10,
  "runtime_ms": 42,
  "memory_kb": 8192,
  "created_at": "2026-01-01T10:00:00Z",
  "finished_at": "2026-01-01T10:00:02Z"
}
```

Do not include private test input, expected output, filesystem paths, sandbox metadata, provider keys, or internal exception traces.

## Error envelope

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The request could not be processed.",
    "request_id": "opaque-correlation-id",
    "details": []
  }
}
```

## API rules

- Validate source size, language allowlist, problem visibility, contest window, and user permissions.
- Add idempotency key support for submission creation.
- Use cursor or page-based pagination with maximum page size.
- Return 401 for unauthenticated, 403 for unauthorized, 404 for inaccessible resources, 409 for state conflicts, 422 for invalid payloads, and 429 for rate limits.
- Never trust client-supplied verdict, runtime, memory, score, user ID, or contest timestamp.
