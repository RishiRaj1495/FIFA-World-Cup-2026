# Contributing

## Code style

Backend code is linted and formatted with [ruff](https://docs.astral.sh/ruff/),
configured in `backend/pyproject.toml`:

```bash
cd backend
pip install -r requirements-dev.txt
ruff check .          # lint
ruff format .         # auto-format
```

CI (`.github/workflows/ci.yml`) runs both, plus the full test suite, on
every push and pull request against `main`. A PR that fails lint, format,
or tests will show a failing check.

Style conventions in this codebase:
- **Clean Architecture layering** — `routes/` only parse/validate HTTP
  input and call a service; `services/` hold all business logic and stay
  framework-agnostic; `models/` are the shared Pydantic contract; `data/`
  is static reference data. Don't put business logic in a route.
- **Docstrings explain *why*, not just *what***, especially for any
  non-obvious design decision (see existing modules for examples).
- **Prefer dispatch tables over long if/elif chains** for intent- or
  type-based branching (see `concierge_engine.INTENT_FACT_RESOLVERS`).
- **Every new service function should be a pure function** where
  possible, so it's testable without spinning up HTTP.

## Testing

```bash
cd backend
pip install -r requirements.txt
pytest -v
```

New logic should ship with tests in the same PR. Tests are organized by
the module they cover (`tests/test_<module>.py`), and route-level tests
use FastAPI's `TestClient` rather than mocking the ASGI layer.

## No secrets, ever

This project intentionally has zero external dependencies or API keys.
If you're contributing a feature, keep it that way — the whole point of
this architecture is that it never requires a reviewer, evaluator, or
new contributor to configure any credential to run it. See `SECURITY.md`
for the full rationale.
