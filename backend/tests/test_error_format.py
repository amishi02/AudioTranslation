"""P2-TEST-004: unknown route returns ErrorResponse envelope."""

from fastapi.testclient import TestClient

from app.main import app


def test_unknown_route_returns_error_envelope() -> None:
    client = TestClient(app)
    resp = client.get("/api/v1/nonexistent")
    assert resp.status_code == 404
    data = resp.json()
    # Must be ErrorResponse shape, not HTML
    assert "error" in data
    assert "code" in data
    assert "message" in data
    assert data["code"] == "NOT_FOUND"


def test_error_envelope_has_no_stack() -> None:
    client = TestClient(app)
    resp = client.get("/this-does-not-exist")
    data = resp.json()
    # Ensure no stack trace leaked
    assert "traceback" not in str(data).lower()
    assert "stack" not in str(data).lower()
