from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_crowd_status_endpoint_shape():
    response = client.get("/api/crowd-status")
    assert response.status_code == 200
    body = response.json()
    assert "gates" in body
    assert "recommended_gate" in body
    assert len(body["gates"]) == 4


def test_accessibility_info_endpoint_default():
    response = client.get("/api/accessibility-info")
    assert response.status_code == 200
    body = response.json()
    assert body["accessibility_need"] == "none"
    assert "nearest_gate" in body


def test_accessibility_info_endpoint_with_need():
    response = client.get("/api/accessibility-info", params={"need": "wheelchair"})
    assert response.status_code == 200
    body = response.json()
    assert body["accessibility_need"] == "wheelchair"
    assert any("accessible" in f.lower() or "step-free" in f.lower() for f in body["facilities"])


def test_stadium_gates_endpoint():
    response = client.get("/api/stadium/gates")
    assert response.status_code == 200
    assert len(response.json()) == 4


def test_chat_endpoint_runs_fully_offline():
    """The /api/chat endpoint requires no configuration or external services."""
    response = client.post("/api/chat", json={"message": "Where is the restroom?", "language": "en"})
    assert response.status_code == 200
    body = response.json()
    assert body["reply"]
    assert body["language"] == "en"
    assert "restroom" in body["reply"].lower()


def test_chat_endpoint_rejects_blank_message():
    response = client.post("/api/chat", json={"message": "   ", "language": "en"})
    assert response.status_code == 422


def test_chat_endpoint_rejects_invalid_language():
    response = client.post("/api/chat", json={"message": "hi", "language": "xx"})
    assert response.status_code == 422
