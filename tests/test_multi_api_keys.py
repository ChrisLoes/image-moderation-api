"""Test multiple API keys functionality"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)

# Test image (minimal PNG)
MINIMAL_PNG = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
    b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01'
    b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
)


class TestMultipleApiKeys:
    """Test that multiple API keys work correctly"""

    def test_valid_dev_api_key(self):
        """Test with first valid API key (dev)"""
        response = client.post(
            "/faces/blur",
            headers={"X-API-Key": "test-dev-key-12345678901234567890"},
            files={"file": ("test.png", MINIMAL_PNG, "image/png")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "processed_image_base64" in data

    def test_valid_prod_api_key(self):
        """Test with second valid API key (prod)"""
        response = client.post(
            "/faces/blur",
            headers={"X-API-Key": "test-prod-key-abcdefghijklmnopqrst"},
            files={"file": ("test.png", MINIMAL_PNG, "image/png")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "processed_image_base64" in data

    def test_invalid_api_key(self):
        """Test with completely wrong API key - should fail"""
        response = client.post(
            "/faces/blur",
            headers={"X-API-Key": "invalid-key-12345"},
            files={"file": ("test.png", MINIMAL_PNG, "image/png")},
        )
        assert response.status_code == 401
        assert "Invalid or missing API key" in response.json()["detail"]

    def test_missing_api_key(self):
        """Test without API key - should fail"""
        response = client.post(
            "/faces/blur",
            files={"file": ("test.png", MINIMAL_PNG, "image/png")},
        )
        assert response.status_code == 422

    def test_all_valid_keys_in_settings(self):
        """Verify all configured API keys are loaded"""
        valid_keys = settings.valid_api_keys
        assert len(valid_keys) == 2
        assert "test-dev-key-12345678901234567890" in valid_keys
        assert "test-prod-key-abcdefghijklmnopqrst" in valid_keys

    def test_dev_key_for_nsfw_endpoint(self):
        """Test dev key works on NSFW endpoint too"""
        response = client.post(
            "/nsfw/check",
            headers={"X-API-Key": "test-dev-key-12345678901234567890"},
            files={"file": ("test.png", MINIMAL_PNG, "image/png")},
        )
        assert response.status_code in [200, 503]  # 503 if model not loaded
        assert response.json()["success"] is True or "not loaded" in response.json().get("detail", "")

    def test_prod_key_for_nsfw_endpoint(self):
        """Test prod key works on NSFW endpoint too"""
        response = client.post(
            "/nsfw/check",
            headers={"X-API-Key": "test-prod-key-abcdefghijklmnopqrst"},
            files={"file": ("test.png", MINIMAL_PNG, "image/png")},
        )
        assert response.status_code in [200, 503]  # 503 if model not loaded
        assert response.json()["success"] is True or "not loaded" in response.json().get("detail", "")

    def test_invalid_key_for_nsfw_endpoint(self):
        """Test invalid key fails on NSFW endpoint"""
        response = client.post(
            "/nsfw/check",
            headers={"X-API-Key": "wrong-key"},
            files={"file": ("test.png", MINIMAL_PNG, "image/png")},
        )
        assert response.status_code == 401
        assert "Invalid or missing API key" in response.json()["detail"]
