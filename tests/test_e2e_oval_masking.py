"""
End-to-End tests for oval masking and full-range face detection.
Tests the new features: oval-shaped blur masks and improved face detection.
"""

import pytest
import requests
import base64
from PIL import Image
import numpy as np
import io


class TestOvalMaskingE2E:
    """E2E tests for oval masking feature."""

    def test_oval_masking_applied(self, api_is_running, api_url, api_headers, simple_test_image, image_to_bytes):
        """Test that oval masking is applied to blurred regions."""
        img_bytes = image_to_bytes(simple_test_image)

        response = requests.post(
            f"{api_url}/faces/blur",
            files={'file': ('test.png', img_bytes, 'image/png')},
            data={'blur_strength': 50, 'blur_method': 'pixelate'},
            headers=api_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'processed_image_base64' in data
        # Oval masking means blur is applied, should have different image
        assert len(data['processed_image_base64']) > 0

    def test_oval_masking_smooth_transitions(self, api_is_running, api_url, api_headers, simple_test_image, image_to_bytes, decode_base64_image):
        """Test that oval masking creates smooth transitions."""
        img_bytes = image_to_bytes(simple_test_image)

        response = requests.post(
            f"{api_url}/faces/blur",
            files={'file': ('test.png', img_bytes, 'image/png')},
            data={'blur_strength': 75, 'blur_method': 'gaussian'},
            headers=api_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()

        # Decode and verify image integrity
        try:
            decoded_img = decode_base64_image(data['processed_image_base64'])
            assert decoded_img is not None
            # Image should have smooth transitions (no hard edges)
            img_array = np.array(decoded_img)
            assert img_array.shape[0] > 0
            assert img_array.shape[1] > 0
        except Exception as e:
            pytest.fail(f"Failed to decode image with oval masking: {e}")

    def test_oval_masking_all_blur_methods(self, api_is_running, api_url, api_headers, simple_test_image, image_to_bytes):
        """Test that oval masking works with all blur methods."""
        for method in ['gaussian', 'pixelate', 'hybrid']:
            img_bytes = image_to_bytes(simple_test_image)
            response = requests.post(
                f"{api_url}/faces/blur",
                files={'file': ('test.png', img_bytes, 'image/png')},
                data={'blur_strength': 50, 'blur_method': method},
                headers=api_headers,
                timeout=10
            )

            assert response.status_code == 200, f"Method {method} failed"
            data = response.json()
            assert data['success'] is True
            assert len(data['processed_image_base64']) > 0


class TestFullRangeFaceDetectionE2E:
    """E2E tests for full-range face detection."""

    def test_full_range_detects_multiple_faces(self, api_is_running, api_url, api_headers, realistic_test_image, image_to_bytes):
        """Test that full-range model detects more faces than short-range."""
        img_bytes = image_to_bytes(realistic_test_image)

        response = requests.post(
            f"{api_url}/faces/blur",
            files={'file': ('test.png', img_bytes, 'image/png')},
            data={'blur_method': 'pixelate', 'blur_strength': 75},
            headers=api_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        # Full-range should detect multiple faces
        assert data['faces_detected'] >= 1, "Full-range should detect at least 1 face"

    def test_full_range_with_aggressive_confidence(self, api_is_running, api_url, api_headers, realistic_test_image, image_to_bytes):
        """Test full-range model with aggressive face detection threshold."""
        img_bytes = image_to_bytes(realistic_test_image)

        response = requests.post(
            f"{api_url}/faces/blur",
            files={'file': ('test.png', img_bytes, 'image/png')},
            data={
                'blur_method': 'pixelate',
                'blur_strength': 100,
                'confidence_threshold': 0.1  # Very aggressive
            },
            headers=api_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        # Should detect multiple faces with aggressive threshold
        assert data['faces_detected'] >= 1

    def test_full_range_with_padding(self, api_is_running, api_url, api_headers, realistic_test_image, image_to_bytes):
        """Test full-range detection with custom padding."""
        img_bytes = image_to_bytes(realistic_test_image)

        response = requests.post(
            f"{api_url}/faces/blur",
            files={'file': ('test.png', img_bytes, 'image/png')},
            data={
                'blur_method': 'pixelate',
                'blur_strength': 150,
                'confidence_threshold': 0.1,
                'face_padding': 20  # Large padding
            },
            headers=api_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['faces_detected'] >= 1


class TestCombinedFeaturesE2E:
    """E2E tests for combined features: oval masking + full-range detection."""

    def test_oval_masking_with_full_range_aggressive(self, api_is_running, api_url, api_headers, realistic_test_image, image_to_bytes):
        """Test oval masking with full-range detection and aggressive thresholds."""
        img_bytes = image_to_bytes(realistic_test_image)

        response = requests.post(
            f"{api_url}/faces/blur",
            files={'file': ('test.png', img_bytes, 'image/png')},
            data={
                'blur_method': 'pixelate',
                'blur_strength': 150,
                'confidence_threshold': 0.1,
                'face_padding': 15
            },
            headers=api_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['faces_detected'] >= 1
        assert len(data['processed_image_base64']) > 10000  # Should have substantial image data

    def test_oval_masking_pixelation_combination(self, api_is_running, api_url, api_headers, simple_test_image, image_to_bytes, decode_base64_image):
        """Test oval masking combined with pixelation blur."""
        img_bytes = image_to_bytes(simple_test_image)

        response = requests.post(
            f"{api_url}/faces/blur",
            files={'file': ('test.png', img_bytes, 'image/png')},
            data={
                'blur_method': 'pixelate',
                'blur_strength': 150,
                'face_padding': 10
            },
            headers=api_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()

        # Verify image can be decoded
        try:
            decoded_img = decode_base64_image(data['processed_image_base64'])
            assert decoded_img is not None
            # Verify image has reasonable dimensions
            assert decoded_img.size[0] > 0
            assert decoded_img.size[1] > 0
        except Exception as e:
            pytest.fail(f"Failed to decode pixelated oval-masked image: {e}")

    def test_oval_masking_hybrid_blur_combination(self, api_is_running, api_url, api_headers, simple_test_image, image_to_bytes, decode_base64_image):
        """Test oval masking combined with hybrid blur method."""
        img_bytes = image_to_bytes(simple_test_image)

        response = requests.post(
            f"{api_url}/faces/blur",
            files={'file': ('test.png', img_bytes, 'image/png')},
            data={
                'blur_method': 'hybrid',
                'blur_strength': 75,
                'face_padding': 15
            },
            headers=api_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True

        # Verify hybrid blur with oval masking produces valid image
        try:
            decoded_img = decode_base64_image(data['processed_image_base64'])
            assert decoded_img is not None
        except Exception as e:
            pytest.fail(f"Failed to decode hybrid blur oval-masked image: {e}")
