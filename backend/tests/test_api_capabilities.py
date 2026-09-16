"""P2-TEST-003: /api/v1/capabilities returns languages & pipeline."""

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


def test_capabilities_returns_languages_and_pipeline() -> None:
    client = TestClient(app)
    resp = client.get("/api/v1/capabilities")
    assert resp.status_code == 200
    data = resp.json()
    assert "supported_languages" in data
    assert isinstance(data["supported_languages"], list)
    # At least the default minimal list
    for lang in settings.supported_languages:
        assert lang in data["supported_languages"]
    assert "pipeline_types" in data
    assert "cascaded" in data["pipeline_types"]
    assert "unified" in data["pipeline_types"]
    assert "default_pipeline" in data
    assert "version" in data
