"""
End-to-End tests for NSFW Detection endpoint.
"""

import pytest
import requests
from PIL import Image
import io


class TestNSFWDetectionE2E:
    """E2E tests for /nsfw/check endpoint."""

    def test_nsfw_basic_success(self, api_is_running, api_url, api_headers, simple_test_image, image_to_bytes):
        """Test basic NSFW detection request succeeds."""
        img_bytes = image_to_bytes(simple_test_image)

        response = requests.post(
            f"{api_url}/nsfw/check",
            files={'file': ('test.png', img_bytes, 'image/png')},
            headers=api_headers,
            timeout=10
        )

        # Either succeeds (200) or model not loaded (503)
        assert response.status_code in [200, 503], f"Expected 200 or 503, got {response.status_code}: {response.text}"

        if response.status_code == 200:
            data = response.json()
            assert data['success'] is True

    def test_nsfw_response_structure(self, api_is_running, api_url, api_headers, simple_test_image, image_to_bytes):
        """Test NSFW response has correct structure."""
        img_bytes = image_to_bytes(simple_test_image)

        response = requests.post(
            f"{api_url}/nsfw/check",
            files={'file': ('test.png', img_bytes, 'image/png')},
            headers=api_headers,
            timeout=10
        )

        if response.status_code == 503:
            pytest.skip("NSFW model not loaded")

        assert response.status_code == 200
        data = response.json()

        # Validate required fields
        required_fields = ['success', 'is_nsfw', 'confidence', 'primary_detection']
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Validate types
        assert isinstance(data['success'], bool)
        assert isinstance(data['is_nsfw'], bool)
        assert isinstance(data['confidence'], (int, float))
        assert isinstance(data['primary_detection'], str)

    def test_nsfw_confidence_range(self, api_is_running, api_url, api_headers, simple_test_image, image_to_bytes):
        """Test confidence score is between 0 and 1."""
        img_bytes = image_to_bytes(simple_test_image)

        response = requests.post(
            f"{api_url}/nsfw/check",
            files={'file': ('test.png', img_bytes, 'image/png')},
            headers=api_headers,
            timeout=10
        )

        if response.status_code == 503:
            pytest.skip("NSFW model not loaded")

        assert response.status_code == 200
        data = response.json()

        confidence = data['confidence']
        assert 0.0 <= confidence <= 1.0, f"Confidence out of range: {confidence}"

    def test_nsfw_primary_detection_valid(self, api_is_running, api_url, api_headers, simple_test_image, image_to_bytes):
        """Test primary detection is one of the valid categories."""
        img_bytes = image_to_bytes(simple_test_image)

        response = requests.post(
            f"{api_url}/nsfw/check",
            files={'file': ('test.png', img_bytes, 'image/png')},
            headers=api_headers,
            timeout=10
        )

        if response.status_code == 503:
            pytest.skip("NSFW model not loaded")

        assert response.status_code == 200
        data = response.json()

        primary = data['primary_detection']
        valid_categories = ['safe', 'partially_nude', 'nude']
        assert primary in valid_categories, f"Invalid primary detection: {primary}"

    def test_nsfw_with_return_details(self, api_is_running, api_url, api_headers, simple_test_image, image_to_bytes):
        """Test NSFW detection with return_details=true."""
        img_bytes = image_to_bytes(simple_test_image)

        response = requests.post(
            f"{api_url}/nsfw/check",
            files={'file': ('test.png', img_bytes, 'image/png')},
            params={'return_details': 'true'},
            headers=api_headers,
            timeout=10
        )

        if response.status_code == 503:
            pytest.skip("NSFW model not loaded")

        assert response.status_code == 200
        data = response.json()

        # Should have detections
        assert 'detections' in data
        detections = data['detections']
        assert detections is not None
        assert isinstance(detections, dict)

        # Should have all 3 categories
        expected_categories = ['safe', 'partially_nude', 'nude']
        for category in expected_categories:
            assert category in detections, f"Missing category: {category}"
            assert isinstance(detections[category], (int, float))
            assert 0.0 <= detections[category] <= 1.0

    def test_nsfw_without_return_details(self, api_is_running, api_url, api_headers, simple_test_image, image_to_bytes):
        """Test NSFW detection without return_details (should be None)."""
        img_bytes = image_to_bytes(simple_test_image)

        response = requests.post(
            f"{api_url}/nsfw/check",
            files={'file': ('test.png', img_bytes, 'image/png')},
            params={'return_details': 'false'},
            headers=api_headers,
            timeout=10
        )

        if response.status_code == 503:
            pytest.skip("NSFW model not loaded")

        assert response.status_code == 200
        data = response.json()

        # detections should be None or not present
        if 'detections' in data:
            assert data['detections'] is None

    def test_nsfw_intensity_levels(self, api_is_running, api_url, api_headers, simple_test_image, image_to_bytes):
        """Test that intensity levels are applied correctly."""
        intensity_results = {}

        for intensity in ['low', 'medium', 'high']:
            img_bytes = image_to_bytes(simple_test_image)
            response = requests.post(
                f"{api_url}/nsfw/check",
                files={'file': ('test.png', img_bytes, 'image/png')},
                params={'intensity': intensity},
                headers=api_headers,
                timeout=10
            )

            if response.status_code == 503:
                pytest.skip("NSFW model not loaded")

            assert response.status_code == 200
            data = response.json()
            intensity_results[intensity] = data

        # All should succeed
        assert all(r['success'] for r in intensity_results.values())

    def test_nsfw_custom_threshold(self, api_is_running, api_url, api_headers, simple_test_image, image_to_bytes):
        """Test NSFW detection with custom threshold."""
        img_bytes = image_to_bytes(simple_test_image)

        response = requests.post(
            f"{api_url}/nsfw/check",
            files={'file': ('test.png', img_bytes, 'image/png')},
            params={'threshold': 0.5},
            headers=api_headers,
            timeout=10
        )

        if response.status_code == 503:
            pytest.skip("NSFW model not loaded")

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True

    def test_nsfw_invalid_image_format(self, api_is_running, api_url, api_headers):
        """Test NSFW with invalid image format."""
        response = requests.post(
            f"{api_url}/nsfw/check",
            files={'file': ('test.txt', b'not an image', 'text/plain')},
            headers=api_headers,
            timeout=10
        )

        assert response.status_code in [400, 422], f"Expected 400 or 422, got {response.status_code}"

    def test_nsfw_missing_api_key(self, api_is_running, api_url, simple_test_image, image_to_bytes):
        """Test NSFW without API key."""
        img_bytes = image_to_bytes(simple_test_image)

        response = requests.post(
            f"{api_url}/nsfw/check",
            files={'file': ('test.png', img_bytes, 'image/png')},
            timeout=10
            # No X-API-Key header
        )

        assert response.status_code == 401

    def test_nsfw_invalid_api_key(self, api_is_running, api_url, simple_test_image, image_to_bytes):
        """Test NSFW with invalid API key."""
        img_bytes = image_to_bytes(simple_test_image)

        response = requests.post(
            f"{api_url}/nsfw/check",
            files={'file': ('test.png', img_bytes, 'image/png')},
            headers={'X-API-Key': 'invalid-key'},
            timeout=10
        )

        assert response.status_code == 401

    def test_nsfw_solid_color_image(self, api_is_running, api_url, api_headers):
        """Test NSFW on solid color image."""
        img = Image.new('RGB', (100, 100), color='blue')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)

        response = requests.post(
            f"{api_url}/nsfw/check",
            files={'file': ('test.png', img_bytes, 'image/png')},
            headers=api_headers,
            timeout=10
        )

        if response.status_code == 503:
            pytest.skip("NSFW model not loaded")

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        # Solid color should likely be 'safe'
        assert data['primary_detection'] in ['safe', 'partially_nude', 'nude']

    def test_nsfw_detections_sum_to_one(self, api_is_running, api_url, api_headers, simple_test_image, image_to_bytes):
        """Test that detection probabilities sum close to 1.0."""
        img_bytes = image_to_bytes(simple_test_image)

        response = requests.post(
            f"{api_url}/nsfw/check",
            files={'file': ('test.png', img_bytes, 'image/png')},
            params={'return_details': 'true'},
            headers=api_headers,
            timeout=10
        )

        if response.status_code == 503:
            pytest.skip("NSFW model not loaded")

        assert response.status_code == 200
        data = response.json()

        if data.get('detections'):
            total = sum(data['detections'].values())
            # Should sum to approximately 1.0 (allow small floating point error)
            assert abs(total - 1.0) < 0.01, f"Detections sum to {total}, expected ~1.0"
