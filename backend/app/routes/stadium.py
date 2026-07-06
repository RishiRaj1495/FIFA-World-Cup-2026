from fastapi import APIRouter

from app.data.stadium_data import AMENITIES, GATES, MATCH_CONTEXT

router = APIRouter(prefix="/api/stadium", tags=["stadium"])


@router.get("/gates")
def list_gates() -> list[dict]:
    """Static gate reference data (id, name, accessibility, amenities)."""
    return GATES


@router.get("/amenities")
def list_amenities() -> dict:
    """Venue-wide amenities keyed by category."""
    return AMENITIES


@router.get("/match-context")
def match_context() -> dict:
    """Basic match/venue context used to ground the concierge's answers."""
    return MATCH_CONTEXT
