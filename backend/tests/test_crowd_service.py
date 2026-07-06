from app.models.schemas import CrowdLevel
from app.services.crowd_service import (
    _estimated_wait_minutes,
    _level_from_occupancy,
    get_best_accessible_gate,
    get_crowd_status,
)


def test_level_from_occupancy_boundaries():
    assert _level_from_occupancy(0) == CrowdLevel.LOW
    assert _level_from_occupancy(40) == CrowdLevel.LOW
    assert _level_from_occupancy(41) == CrowdLevel.MODERATE
    assert _level_from_occupancy(70) == CrowdLevel.MODERATE
    assert _level_from_occupancy(71) == CrowdLevel.HIGH
    assert _level_from_occupancy(90) == CrowdLevel.HIGH
    assert _level_from_occupancy(91) == CrowdLevel.CRITICAL
    assert _level_from_occupancy(100) == CrowdLevel.CRITICAL


def test_estimated_wait_is_monotonic_non_decreasing():
    waits = [_estimated_wait_minutes(p) for p in range(0, 101, 10)]
    assert waits == sorted(waits)


def test_get_crowd_status_returns_all_gates():
    status = get_crowd_status()
    assert len(status.gates) == 4
    gate_ids = {g.gate_id for g in status.gates}
    assert gate_ids == {"A", "B", "C", "D"}


def test_recommended_gate_is_the_lowest_occupancy_gate():
    status = get_crowd_status()
    min_occupancy_gate = min(status.gates, key=lambda g: g.occupancy_percent)
    assert status.recommended_gate == min_occupancy_gate.gate_id


def test_best_accessible_gate_is_wheelchair_accessible():
    gate = get_best_accessible_gate()
    assert gate.wheelchair_accessible is True


def test_occupancy_reading_is_stable_within_same_time_bucket():
    first = get_crowd_status()
    second = get_crowd_status()
    first_by_id = {g.gate_id: g.occupancy_percent for g in first.gates}
    second_by_id = {g.gate_id: g.occupancy_percent for g in second.gates}
    assert first_by_id == second_by_id
