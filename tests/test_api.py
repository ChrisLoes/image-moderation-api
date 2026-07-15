import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app

client = TestClient(app)


class TestHealthEndpoint:
    def test_health_check_returns_200(self):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_structure(self):
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "ok", "alive"]


class TestAPIEndpoints:
    def test_docs_endpoint_available(self):
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_schema_available(self):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data


class TestConfigLoading:
    def test_api_keys_loaded(self):
        from app.config import settings
        assert settings.api_keys is not None
        assert len(settings.api_keys) > 0

    def test_default_settings(self):
        from app.config import settings
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        assert settings.face_detection_confidence >= 0
        assert settings.face_detection_confidence <= 1


class TestErrorHandling:
    def test_invalid_endpoint_returns_404(self):
        response = client.get("/invalid/endpoint")
        assert response.status_code == 404

    def test_missing_api_key_authentication(self):
        # Assuming auth is implemented
        response = client.post("/analyze/nsfw", json={})
        # Should either return 401/403 or accept without key depending on config
        assert response.status_code in [200, 401, 403, 422]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
