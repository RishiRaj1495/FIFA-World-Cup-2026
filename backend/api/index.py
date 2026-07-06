"""
Vercel serverless entrypoint.

Vercel's Python runtime looks for an ASGI-compatible `app` object under
`api/`. This file adds no logic of its own — it just re-exports the same
FastAPI app used for local development, so behavior is identical in both
environments.
"""
from app.main import app  # noqa: F401
