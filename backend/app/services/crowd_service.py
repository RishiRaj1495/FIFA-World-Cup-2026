"""
Crowd intelligence service.

Produces a simulated real-time occupancy reading per gate and derives a
recommendation (which gate to use right now, and why). The simulation is
deterministic-with-jitter so behaviour is explainable and testable, while
still changing over time the way a real IoT footfall sensor feed would.

Swapping `_read_occupancy()` for a call into a real turnstile/camera
analytics API is the only change needed to go from simulation to
production, since everything downstream (recommendation logic, API
response shape) depends only on the occupancy percentage.
"""
import random
from datetime import datetime, timezone

from app.data.stadium_data import GATES
from app.models.schemas import CrowdLevel, GateStatus, CrowdStatusResponse

# Bucket boundaries kept as named constants rather than magic numbers,
# so the thresholds are easy to find and tune from one place.
LOW_MAX = 40
MODERATE_MAX = 70
HIGH_MAX = 90


def _level_from_occupancy(occupancy_percent: int) -> CrowdLevel:
    if occupancy_percent <= LOW_MAX:
        return CrowdLevel.LOW
    if occupancy_percent <= MODERATE_MAX:
        return CrowdLevel.MODERATE
    if occupancy_percent <= HIGH_MAX:
        return CrowdLevel.HIGH
    return CrowdLevel.CRITICAL


def _estimated_wait_minutes(occupancy_percent: int) -> int:
    """Simple monotonic mapping: emptier gate -> near-zero wait."""
    if occupancy_percent <= LOW_MAX:
        return 0
    if occupancy_percent <= MODERATE_MAX:
        return 3
    if occupancy_percent <= HIGH_MAX:
        return 8
    return 15


def _read_occupancy(gate_id: str, minute_bucket: int) -> int:
    """
    Deterministic-with-jitter occupancy reading for a gate at a given
    5-minute time bucket. Deterministic seeding means repeated calls
    within the same bucket return stable results (important for tests
    and for not flickering the UI faster than fans can react to it).
    """
    seed = hash((gate_id, minute_bucket)) & 0xFFFFFFFF
    rng = random.Random(seed)
    base = rng.randint(20, 95)
    return max(0, min(100, base))


def get_crowd_status() -> CrowdStatusResponse:
    now = datetime.now(timezone.utc)
    minute_bucket = now.minute // 5

    gate_statuses: list[GateStatus] = []
    for gate in GATES:
        occupancy = _read_occupancy(gate["gate_id"], minute_bucket)
        gate_statuses.append(
            GateStatus(
                gate_id=gate["gate_id"],
                name=gate["name"],
                crowd_level=_level_from_occupancy(occupancy),
                occupancy_percent=occupancy,
                estimated_wait_minutes=_estimated_wait_minutes(occupancy),
                wheelchair_accessible=gate["wheelchair_accessible"],
            )
        )

    recommended = min(gate_statuses, key=lambda g: g.occupancy_percent)
    reason = (
        f"{recommended.name} currently has the lowest occupancy "
        f"({recommended.occupancy_percent}%) and roughly "
        f"{recommended.estimated_wait_minutes} minute wait."
    )

    return CrowdStatusResponse(
        updated_at=now.isoformat(),
        gates=gate_statuses,
        recommended_gate=recommended.gate_id,
        recommendation_reason=reason,
    )


def get_best_accessible_gate() -> GateStatus:
    """Recommend the least crowded gate among the wheelchair-accessible ones."""
    status = get_crowd_status()
    accessible_gates = [g for g in status.gates if g.wheelchair_accessible]
    return min(accessible_gates, key=lambda g: g.occupancy_percent)
