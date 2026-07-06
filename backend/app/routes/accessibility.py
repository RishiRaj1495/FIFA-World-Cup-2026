from fastapi import APIRouter, Query

from app.data.stadium_data import ACCESSIBILITY_FACILITIES
from app.models.schemas import AccessibilityInfoResponse, AccessibilityNeed
from app.services.crowd_service import get_best_accessible_gate

router = APIRouter(prefix="/api/accessibility-info", tags=["accessibility"])


@router.get("", response_model=AccessibilityInfoResponse)
def accessibility_info(
    need: AccessibilityNeed = Query(default=AccessibilityNeed.NONE),
) -> AccessibilityInfoResponse:
    """Facilities relevant to a fan's accessibility need, plus the best gate to use right now."""
    best_gate = get_best_accessible_gate()
    facilities = ACCESSIBILITY_FACILITIES.get(need.value, ACCESSIBILITY_FACILITIES["none"])

    notes = (
        f"{best_gate.name} is currently the least crowded accessible gate "
        f"({best_gate.occupancy_percent}% occupancy)."
    )

    return AccessibilityInfoResponse(
        accessibility_need=need,
        facilities=facilities,
        nearest_gate=best_gate.gate_id,
        notes=notes,
    )
