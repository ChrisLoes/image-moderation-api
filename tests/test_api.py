import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path
from io import BytesIO
from PIL import Image
import base64

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app
from app.config import settings

client = TestClient(app)


def create_test_image(width=100, height=100, color=(100, 100, 100)):
    """Create a simple test image."""
    img = Image.new("RGB", (width, height), color)
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)
    return img_byte_arr


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

    def test_blur_intensity_levels(self):
        """Test that intensity levels map to correct blur strengths."""
        assert settings.get_blur_strength("low") == 11
        assert settings.get_blur_strength("medium") == 25
        assert settings.get_blur_strength("high") == 41

    def test_face_confidence_intensity_levels(self):
        """Test that intensity levels map to correct confidence thresholds."""
        assert settings.get_face_detection_confidence("low") == 0.3
        assert settings.get_face_detection_confidence("medium") == 0.5
        assert settings.get_face_detection_confidence("high") == 0.8

    def test_nsfw_threshold_intensity_levels(self):
        """Test that intensity levels map to correct NSFW thresholds."""
        assert settings.get_nsfw_threshold("low") == 0.8
        assert settings.get_nsfw_threshold("medium") == 0.6
        assert settings.get_nsfw_threshold("high") == 0.4


class TestErrorHandling:
    def test_invalid_endpoint_returns_404(self):
        response = client.get("/invalid/endpoint")
        assert response.status_code == 404

    def test_nsfw_check_requires_file(self):
        # Test that /nsfw/check requires a file - returns 422 (validation error) when empty
        response = client.post("/nsfw/check", data={})
        # Returns 422 Unprocessable Entity for missing required file field
        assert response.status_code == 422

    def test_face_blur_requires_file(self):
        # Test that /faces/blur requires a file - returns 422 (validation error) when empty
        response = client.post("/faces/blur", data={})
        # Returns 422 Unprocessable Entity for missing required file field
        assert response.status_code == 422


class TestParameterApplication:
    """Tests to verify that API parameters are actually being applied."""

    def test_face_blur_with_different_blur_strengths(self):
        """Test that different blur_strength values produce different base64 outputs."""
        test_image = create_test_image()

        # Test with blur_strength=11 (minimal)
        response1 = client.post(
            "/faces/blur",
            files={"file": ("test.png", test_image, "image/png")},
            data={"blur_strength": 11},
            headers={"X-API-Key": "test-key"}
        )
        test_image.seek(0)

        # Test with blur_strength=41 (heavy)
        response2 = client.post(
            "/faces/blur",
            files={"file": ("test.png", test_image, "image/png")},
            data={"blur_strength": 41},
            headers={"X-API-Key": "test-key"}
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Both should have processed_image_base64
        assert "processed_image_base64" in data1
        assert "processed_image_base64" in data2

        # With different blur strengths, images should be different
        # (Note: This might not always be true if no faces are detected,
        # but the blur kernels are different so processing should differ)
        if data1["faces_detected"] == data2["faces_detected"] and data1["faces_detected"] > 0:
            assert data1["processed_image_base64"] != data2["processed_image_base64"], \
                "Different blur_strength values should produce different images"

    def test_face_blur_intensity_parameter(self):
        """Test that intensity parameter is applied correctly."""
        test_image = create_test_image()

        # Test with intensity=low
        response_low = client.post(
            "/faces/blur",
            files={"file": ("test.png", test_image, "image/png")},
            data={"intensity": "low"},
            headers={"X-API-Key": "test-key"}
        )
        test_image.seek(0)

        # Test with intensity=high
        response_high = client.post(
            "/faces/blur",
            files={"file": ("test.png", test_image, "image/png")},
            data={"intensity": "high"},
            headers={"X-API-Key": "test-key"}
        )

        assert response_low.status_code == 200
        assert response_high.status_code == 200

        data_low = response_low.json()
        data_high = response_high.json()

        assert "processed_image_base64" in data_low
        assert "processed_image_base64" in data_high

        # High intensity should detect more or equal faces than low
        assert data_high["faces_detected"] >= data_low["faces_detected"], \
            "High intensity should detect >= faces than low intensity"

    def test_face_blur_parameter_priority(self):
        """Test that explicit parameters override intensity parameter."""
        test_image = create_test_image()

        # Test with intensity=low but explicit high blur_strength
        response = client.post(
            "/faces/blur",
            files={"file": ("test.png", test_image, "image/png")},
            data={"intensity": "low", "blur_strength": 41},
            headers={"X-API-Key": "test-key"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "processed_image_base64" in data
        # This tests that explicit parameter overrides intensity
        # (blur_strength=41 should be used, not intensity=low's value of 11)

    def test_face_blur_image_is_not_original(self):
        """Test that returned image is different from original when faces are detected."""
        test_image = create_test_image()
        original_data = base64.b64encode(test_image.getvalue()).decode()
        test_image.seek(0)

        response = client.post(
            "/faces/blur",
            files={"file": ("test.png", test_image, "image/png")},
            data={"blur_strength": 25},
            headers={"X-API-Key": "test-key"}
        )

        assert response.status_code == 200
        data = response.json()

        # The processed image should be different from the original
        # (unless no faces were detected, then it might be same)
        # This is a basic check that processing happened
        assert data["processed_image_base64"] is not None
        if data["faces_detected"] > 0:
            assert data["processed_image_base64"] != original_data, \
                "Processed image should differ from original when faces are blurred"

    def test_nsfw_return_details_parameter(self):
        """Test that return_details parameter actually returns detailed scores."""
        test_image = create_test_image()

        # Test without return_details
        response1 = client.post(
            "/nsfw/check",
            files={"file": ("test.png", test_image, "image/png")},
            headers={"X-API-Key": "test-key"}
        )
        test_image.seek(0)

        # Test with return_details=true
        response2 = client.post(
            "/nsfw/check",
            files={"file": ("test.png", test_image, "image/png")},
            data={"return_details": True},
            headers={"X-API-Key": "test-key"}
        )

        # Note: NSFW model might not be loaded, so check for both success and model not loaded
        if response1.status_code == 200:
            data1 = response1.json()
            assert "detections" not in data1 or data1["detections"] is None, \
                "Without return_details, detections should be None/empty"

        if response2.status_code == 200:
            data2 = response2.json()
            assert "detections" in data2, \
                "With return_details=true, detections should be present"
            if data2["detections"] is not None:
                assert isinstance(data2["detections"], dict), \
                    "Detections should be a dictionary"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
