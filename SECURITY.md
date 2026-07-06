# Security

This project has no external service dependencies and no secrets to
manage. The practices below are what's actually implemented in the code,
not aspirational — each one is backed by an automated test.

## No credentials, anywhere

There is no API key, token, or credential of any kind in this codebase.
The concierge (`app/services/concierge_engine.py`) runs entirely
in-process. This isn't just a convenience — it removes an entire class of
risk (leaked keys, misconfigured secrets, third-party outages) by
construction rather than by careful handling.

## Input validation

Every request body is validated by Pydantic models
(`app/models/schemas.py`) before it reaches any business logic:
- `message` is bounded to 1–1000 characters and rejected if blank
  (`ChatRequest.strip_message`).
- `language` and `accessibility_need` are constrained enums — an invalid
  value is rejected with a 422 before it can reach application code, not
  silently coerced.
- `gate` and `session_id` are length-bounded strings.

See `tests/test_routes.py` for the tests that lock this in
(`test_chat_endpoint_rejects_blank_message`,
`test_chat_endpoint_rejects_invalid_language`).

## CORS

Cross-origin access is restricted to an explicit allow-list
(`ALLOWED_ORIGINS` env var, parsed in `app/core/config.py`), not a
wildcard. Only `GET`/`POST` are permitted.

## Rate limiting

`app/core/rate_limit.py` implements a fixed-window limiter (30
requests/60 seconds per client, by IP) applied to `/api/chat` via
`RateLimitMiddleware`. It's in-memory and single-process by design —
appropriate for this deployment's scale, and documented as an assumption
in the main README. The same `is_allowed(key)` interface is what a
Redis-backed limiter would expose if this were ever scaled across
multiple processes, so swapping the backend wouldn't change any calling
code. Tests: `tests/test_rate_limit.py`, `tests/test_security.py`.

## HTTP security headers

`app/core/security_headers.py` adds `X-Content-Type-Options: nosniff`,
`X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, and a restrictive
`Permissions-Policy` to every response. Test:
`test_security_headers_present_on_every_response`.

## No dynamic code execution

No `eval`, `exec`, `pickle`, shell invocation, or dynamic import of
untrusted input anywhere in the codebase. The only "dynamic" behavior is
keyword matching against a fixed, developer-authored dictionary
(`INTENT_KEYWORDS`).

## Reporting an issue

This is a hackathon submission without a maintained release cycle. If you
find an issue while reviewing it, please open a GitHub issue on the repo.
