"""
Application entrypoint.

Wires up FastAPI, CORS, and all route modules. Kept intentionally thin:
no business logic lives here, only composition, so the app is easy to
reason about and the routes/services stay independently testable.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routes import chat, crowd, accessibility, stadium

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="GenAI-enabled multilingual fan concierge and crowd intelligence API "
    "for FIFA World Cup 2026 stadium operations.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(crowd.router)
app.include_router(accessibility.router)
app.include_router(stadium.router)


@app.get("/api/health", tags=["health"])
def health_check() -> dict:
    """Liveness probe used by uptime checks and local smoke tests."""
    return {"status": "ok", "app": settings.app_name, "environment": settings.environment}
