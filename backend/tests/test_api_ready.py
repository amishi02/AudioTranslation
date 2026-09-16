"""P2-TEST-002: /health/ready returns readiness fields."""

from fastapi.testclient import TestClient

from app.main import app


def test_ready_returns_fields() -> None:
    client = TestClient(app)
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert "model_ready" in data
    assert data["model_ready"] is True
    assert "pipeline" in data
    assert "version" in data
