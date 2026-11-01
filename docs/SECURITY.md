# Security Requirements

## Critical: untrusted code

- Never use Python `subprocess`, `exec`, `eval`, shell commands, or temporary files in the API server to run submitted code.
- Use Judge0 CE or another maintained sandboxed execution service.
- Prefer self-hosted judge infrastructure for a serious demo; configure isolated worker nodes.
- Apply CPU, wall-time, memory, process-count, output-size, filesystem, and network restrictions.
- Disable outbound network access from execution containers unless a problem explicitly requires it.
- Run containers as non-root with dropped capabilities, seccomp/AppArmor where supported, read-only base filesystem, ephemeral workspace, and resource quotas.
- Keep judge service private on an internal Docker network.
- Treat compiler output and program output as untrusted strings; escape them in the UI.

## Application security

- Hash passwords using Argon2id; never store plaintext passwords.
- Use secure, HttpOnly, SameSite cookies if cookie sessions are chosen; implement CSRF protections.
- Validate all inputs with Pydantic and frontend schemas; backend is authoritative.
- Add rate limits for login, run, submit, AI, registration, and password reset.
- Use parameterized queries/ORM; never concatenate SQL from user input.
- Apply RBAC to every admin and problem-authoring endpoint.
- Protect against XSS, CSRF, SSRF, IDOR, SQL injection, and mass assignment.
- Add upload limits and validate MIME/type if uploads are introduced.
- Keep secrets in environment/secret manager; do not use `NEXT_PUBLIC_` for secrets.
- Redact code, tokens, passwords, hidden tests, and provider responses from logs.
- Add audit trails for privileged operations.

## AI-specific controls

- Treat user-provided code and problem text as untrusted prompt content.
- Do not send hidden tests, expected answers, private editorial, or another user's data to an LLM.
- Do not allow model output to invoke tools, change scores, or run commands.
- Enforce server-side model allowlist, token budget, timeout, quotas, and output moderation.
- Tell users AI suggestions can be inaccurate.
