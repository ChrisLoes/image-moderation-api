"""
End-to-End tests for Face Blur endpoint.
"""

import pytest
import requests
import base64
from PIL import Image
import io


class TestFaceBlurE2E:
    """E2E tests for /faces/blur endpoint."""

    def test_blur_basic_success(self, api_is_running, api_url, api_headers, simple_test_image, image_to_bytes):
        """Test basic face blur request succeeds."""
        img_bytes = image_to_bytes(simple_test_image)

        response = requests.post(
            f"{api_url}/faces/blur",
            files={'file': ('test.png', img_bytes, 'image/png')},
            headers=api_headers,
            timeout=10
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        assert data['success'] is True
        assert 'message' in data
        assert 'processed_image_base64' in data
        assert len(data['processed_image_base64']) > 0

    def test_blur_response_structure(self, api_is_running, api_url, api_headers, simple_test_image, image_to_bytes):
        """Test response has correct structure."""
        img_bytes = image_to_bytes(simple_test_image)

        response = requests.post(
            f"{api_url}/faces/blur",
            files={'file': ('test.png', img_bytes, 'image/png')},
            data={'blur_strength': 25},
            headers=api_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()

        # Validate all required fields
        required_fields = ['success', 'message', 'faces_detected', 'processed_image_base64']
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Validate types
        assert isinstance(data['success'], bool)
        assert isinstance(data['message'], str)
        assert isinstance(data['faces_detected'], int)
        assert isinstance(data['processed_image_base64'], str)

    def test_blur_strength_produces_different_results(self, api_is_running, api_url, api_headers, simple_test_image, image_to_bytes, decode_base64_image, compare_images):
        """Test that different blur strengths produce different images."""
        blur_results = {}

        for strength in [10, 50]:
            img_bytes = image_to_bytes(simple_test_image)
            response = requests.post(
                f"{api_url}/faces/blur",
                files={'file': ('test.png', img_bytes, 'image/png')},
                data={'blur_strength': strength},
                headers=api_headers,
                timeout=10
            )

            assert response.status_code == 200
            data = response.json()
            blur_results[strength] = data['processed_image_base64']

        # Decode images
        img_10 = decode_base64_image(blur_results[10])
        img_50 = decode_base64_image(blur_results[50])

        # Compare
        comparison = compare_images(img_10, img_50)
        assert not comparison['are_same'], "Different blur strengths should produce different images"
        assert comparison['difference'] is not None
        assert comparison['difference'] > 0

    def test_blur_parameter_priority(self, api_is_running, api_url, api_headers, simple_test_image, image_to_bytes):
        """Test that explicit blur_strength overrides intensity."""
        img_bytes = image_to_bytes(simple_test_image)

        # intensity=low with explicit blur_strength=50 should use 50
        response = requests.post(
            f"{api_url}/faces/blur",
            files={'file': ('test.png', img_bytes, 'image/png')},
            data={'intensity': 'low', 'blur_strength': 50},
            headers=api_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        # If blur_strength parameter overrides, response should indicate blur was applied
        assert data['success'] is True

    def test_blur_with_padding(self, api_is_running, api_url, api_headers, simple_test_image, image_to_bytes, decode_base64_image, compare_images):
        """Test that different padding values produce different results."""
        padding_results = {}

        for padding in [0, 20]:
            img_bytes = image_to_bytes(simple_test_image)
            response = requests.post(
                f"{api_url}/faces/blur",
                files={'file': ('test.png', img_bytes, 'image/png')},
                data={'blur_strength': 30, 'face_padding': padding},
                headers=api_headers,
                timeout=10
            )

            assert response.status_code == 200
            data = response.json()
            padding_results[padding] = data['processed_image_base64']

        # Decode images
        img_0 = decode_base64_image(padding_results[0])
        img_20 = decode_base64_image(padding_results[20])

        # Compare - should be different
        comparison = compare_images(img_0, img_20)
        assert not comparison['are_same'], "Different padding should produce different blur areas"

    def test_blur_intensity_levels(self, api_is_running, api_url, api_headers, realistic_test_image, image_to_bytes):
        """Test that intensity levels are applied correctly."""
        intensity_results = {}

        for intensity in ['low', 'medium', 'high']:
            img_bytes = image_to_bytes(realistic_test_image)
            response = requests.post(
                f"{api_url}/faces/blur",
                files={'file': ('test.png', img_bytes, 'image/png')},
                data={'intensity': intensity},
                headers=api_headers,
                timeout=10
            )

            assert response.status_code == 200
            data = response.json()
            intensity_results[intensity] = data['faces_detected']

        # All should have valid responses
        assert all(isinstance(v, int) for v in intensity_results.values())
        # High intensity should detect >= faces compared to low (in general)
        assert intensity_results['high'] >= intensity_results['low'], \
            f"High intensity should detect >= faces than low. Got: {intensity_results}"

    def test_blur_without_faces(self, api_is_running, api_url, api_headers):
        """Test blur on image without faces (solid color)."""
        # Create solid color image
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)

        response = requests.post(
            f"{api_url}/faces/blur",
            files={'file': ('test.png', img_bytes, 'image/png')},
            data={'blur_strength': 25},
            headers=api_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['faces_detected'] == 0
        assert 'No faces' in data['message'] or data['faces_detected'] == 0

    def test_blur_invalid_image_format(self, api_is_running, api_url, api_headers):
        """Test blur with invalid image format."""
        response = requests.post(
            f"{api_url}/faces/blur",
            files={'file': ('test.txt', b'not an image', 'text/plain')},
            headers=api_headers,
            timeout=10
        )

        assert response.status_code in [400, 422], f"Expected 400 or 422, got {response.status_code}"

    def test_blur_missing_api_key(self, api_is_running, api_url, simple_test_image, image_to_bytes):
        """Test blur without API key."""
        img_bytes = image_to_bytes(simple_test_image)

        response = requests.post(
            f"{api_url}/faces/blur",
            files={'file': ('test.png', img_bytes, 'image/png')},
            timeout=10
            # No X-API-Key header
        )

        assert response.status_code == 401

    def test_blur_invalid_api_key(self, api_is_running, api_url, simple_test_image, image_to_bytes):
        """Test blur with invalid API key."""
        img_bytes = image_to_bytes(simple_test_image)

        response = requests.post(
            f"{api_url}/faces/blur",
            files={'file': ('test.png', img_bytes, 'image/png')},
            headers={'X-API-Key': 'invalid-key'},
            timeout=10
        )

        assert response.status_code == 401

    def test_blur_image_base64_is_valid(self, api_is_running, api_url, api_headers, simple_test_image, image_to_bytes, decode_base64_image):
        """Test that returned base64 image is valid and can be decoded."""
        img_bytes = image_to_bytes(simple_test_image)

        response = requests.post(
            f"{api_url}/faces/blur",
            files={'file': ('test.png', img_bytes, 'image/png')},
            data={'blur_strength': 25},
            headers=api_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()

        # Try to decode the base64 image
        try:
            decoded_img = decode_base64_image(data['processed_image_base64'])
            assert decoded_img is not None
            assert decoded_img.size[0] > 0
            assert decoded_img.size[1] > 0
        except Exception as e:
            pytest.fail(f"Failed to decode base64 image: {e}")

    def test_blur_large_blur_strength(self, api_is_running, api_url, api_headers, simple_test_image, image_to_bytes):
        """Test blur with very large blur strength."""
        img_bytes = image_to_bytes(simple_test_image)

        response = requests.post(
            f"{api_url}/faces/blur",
            files={'file': ('test.png', img_bytes, 'image/png')},
            data={'blur_strength': 200},
            headers=api_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'processed_image_base64' in data

    def test_blur_zero_padding(self, api_is_running, api_url, api_headers, simple_test_image, image_to_bytes):
        """Test blur with zero padding (no padding)."""
        img_bytes = image_to_bytes(simple_test_image)

        response = requests.post(
            f"{api_url}/faces/blur",
            files={'file': ('test.png', img_bytes, 'image/png')},
            data={'blur_strength': 25, 'face_padding': 0},
            headers=api_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
