from fastapi import APIRouter

from app.models.schemas import CrowdStatusResponse
from app.services.crowd_service import get_crowd_status

router = APIRouter(prefix="/api/crowd-status", tags=["crowd"])


@router.get("", response_model=CrowdStatusResponse)
def crowd_status() -> CrowdStatusResponse:
    """Real-time (simulated) occupancy per gate plus a recommended gate to use now."""
    return get_crowd_status()
