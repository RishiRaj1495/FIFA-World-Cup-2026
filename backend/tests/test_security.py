from fastapi.testclient import TestClient

from app.core.rate_limit import chat_rate_limiter
from app.main import app

client = TestClient(app)


def test_security_headers_present_on_every_response():
    response = client.get("/api/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_chat_endpoint_is_rate_limited_after_repeated_requests():
    # Give this test its own clean slate regardless of test execution order.
    chat_rate_limiter._hits.clear()

    payload = {"message": "Where is the restroom?", "language": "en"}
    for _ in range(chat_rate_limiter.max_requests):
        response = client.post("/api/chat", json=payload)
        assert response.status_code == 200

    blocked = client.post("/api/chat", json=payload)
    assert blocked.status_code == 429

    chat_rate_limiter._hits.clear()


def test_non_rate_limited_endpoints_are_unaffected():
    chat_rate_limiter._hits.clear()
    for _ in range(chat_rate_limiter.max_requests + 5):
        response = client.get("/api/crowd-status")
        assert response.status_code == 200


def test_chat_endpoint_rate_limit_with_proxy_headers():
    chat_rate_limiter._hits.clear()
    payload = {"message": "Where is the restroom?", "language": "en"}

    # Request from proxy IP but distinct client IPs in X-Forwarded-For should be tracked independently
    for i in range(chat_rate_limiter.max_requests):
        headers = {"X-Forwarded-For": f"192.168.1.{i}, 10.0.0.1"}
        response = client.post("/api/chat", json=payload, headers=headers)
        assert response.status_code == 200

    # A single client IP exceeding the limit should be blocked
    headers_target = {"X-Forwarded-For": "192.168.2.1, 10.0.0.1"}
    for _ in range(chat_rate_limiter.max_requests):
        response = client.post("/api/chat", json=payload, headers=headers_target)
        assert response.status_code == 200

    # The 31st request from the same client IP should be rate-limited
    blocked_response = client.post("/api/chat", json=payload, headers=headers_target)
    assert blocked_response.status_code == 429

    chat_rate_limiter._hits.clear()
