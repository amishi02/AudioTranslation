"""Backend smoke test — Phase 1 P1-TEST-001.

Verifies that the FastAPI app is importable and has expected metadata,
plus that core config and logging are functional without requiring .env
or running server. See implementation-plan/phase1.md P1-TEST-001.
"""

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


def test_app_importable() -> None:
    assert app is not None
    # Title comes from settings.app_name via app/main.py wiring (P1-BE-002)
    assert app.title == settings.app_name
    assert app.title == "Real-Time Audio Translation API"


def test_health_endpoint_registered() -> None:
    # Use TestClient to verify /health is reachable (works with _IncludedRouter)
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_config_loads() -> None:
    # P1-BE-001: settings loads via pydantic-settings in dev and test
    assert settings.app_env in ("development", "production", "test")
    assert settings.host
    assert settings.port >= 1
    assert isinstance(settings.cors_origins, list)
    assert len(settings.cors_origins) >= 1
