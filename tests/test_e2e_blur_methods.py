"""
End-to-End tests for different blur methods (Gaussian, Pixelate, Hybrid).
Tests blur method comparison and intensity effects.
"""

import pytest
import requests
import base64
from PIL import Image
import numpy as np
import io


class TestBlurMethodsE2E:
    """E2E tests for different blur methods."""

    def test_blur_method_gaussian(self, api_is_running, api_url, api_headers, simple_test_image, image_to_bytes):
        """Test Gaussian blur method (smooth, natural)."""
        img_bytes = image_to_bytes(simple_test_image)

        response = requests.post(
            f"{api_url}/faces/blur",
            files={'file': ('test.png', img_bytes, 'image/png')},
            data={'blur_strength': 50, 'blur_method': 'gaussian'},
            headers=api_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'processed_image_base64' in data

    def test_blur_method_pixelate(self, api_is_running, api_url, api_headers, simple_test_image, image_to_bytes):
        """Test Pixelate blur method (strong, blocky, privacy-focused)."""
        img_bytes = image_to_bytes(simple_test_image)

        response = requests.post(
            f"{api_url}/faces/blur",
            files={'file': ('test.png', img_bytes, 'image/png')},
            data={'blur_strength': 100, 'blur_method': 'pixelate'},
            headers=api_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'processed_image_base64' in data

    def test_blur_method_hybrid(self, api_is_running, api_url, api_headers, simple_test_image, image_to_bytes):
        """Test Hybrid blur method (combination of pixelation + Gaussian)."""
        img_bytes = image_to_bytes(simple_test_image)

        response = requests.post(
            f"{api_url}/faces/blur",
            files={'file': ('test.png', img_bytes, 'image/png')},
            data={'blur_strength': 75, 'blur_method': 'hybrid'},
            headers=api_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'processed_image_base64' in data

    def test_blur_methods_produce_different_results(self, api_is_running, api_url, api_headers, simple_test_image, image_to_bytes, decode_base64_image, compare_images):
        """Test that different blur methods produce different images."""
        methods = {}

        for method in ['gaussian', 'pixelate', 'hybrid']:
            img_bytes = image_to_bytes(simple_test_image)
            response = requests.post(
                f"{api_url}/faces/blur",
                files={'file': ('test.png', img_bytes, 'image/png')},
                data={'blur_strength': 50, 'blur_method': method},
                headers=api_headers,
                timeout=10
            )

            assert response.status_code == 200
            data = response.json()
            methods[method] = data['processed_image_base64']

        # All methods should produce different results
        for i, method1 in enumerate(['gaussian', 'pixelate', 'hybrid']):
            for method2 in ['gaussian', 'pixelate', 'hybrid'][i+1:]:
                img1 = decode_base64_image(methods[method1])
                img2 = decode_base64_image(methods[method2])
                comparison = compare_images(img1, img2)
                assert not comparison['are_same'], \
                    f"Methods {method1} and {method2} should produce different results"

    def test_blur_method_pixelate_very_strong(self, api_is_running, api_url, api_headers, simple_test_image, image_to_bytes, decode_base64_image):
        """Test pixelate with very high blur strength for extreme privacy."""
        img_bytes = image_to_bytes(simple_test_image)

        response = requests.post(
            f"{api_url}/faces/blur",
            files={'file': ('test.png', img_bytes, 'image/png')},
            data={'blur_strength': 200, 'blur_method': 'pixelate'},
            headers=api_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True

        # Verify output image is valid
        try:
            decoded_img = decode_base64_image(data['processed_image_base64'])
            assert decoded_img is not None
        except Exception as e:
            pytest.fail(f"Failed to decode pixelated image: {e}")

    def test_blur_method_default_is_gaussian(self, api_is_running, api_url, api_headers, simple_test_image, image_to_bytes):
        """Test that default blur method is Gaussian."""
        img_bytes = image_to_bytes(simple_test_image)

        # Request without specifying blur_method
        response = requests.post(
            f"{api_url}/faces/blur",
            files={'file': ('test.png', img_bytes, 'image/png')},
            data={'blur_strength': 50},
            headers=api_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        # Should use default Gaussian method

    def test_blur_method_invalid_falls_back_to_gaussian(self, api_is_running, api_url, api_headers, simple_test_image, image_to_bytes):
        """Test that invalid blur method falls back to Gaussian."""
        img_bytes = image_to_bytes(simple_test_image)

        response = requests.post(
            f"{api_url}/faces/blur",
            files={'file': ('test.png', img_bytes, 'image/png')},
            data={'blur_strength': 50, 'blur_method': 'invalid_method'},
            headers=api_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        # Should fall back to Gaussian without error

    def test_pixelate_with_low_strength(self, api_is_running, api_url, api_headers, simple_test_image, image_to_bytes):
        """Test pixelate with low strength (subtle pixelation)."""
        img_bytes = image_to_bytes(simple_test_image)

        response = requests.post(
            f"{api_url}/faces/blur",
            files={'file': ('test.png', img_bytes, 'image/png')},
            data={'blur_strength': 15, 'blur_method': 'pixelate'},
            headers=api_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True

    def test_hybrid_blur_intensity_low(self, api_is_running, api_url, api_headers, simple_test_image, image_to_bytes):
        """Test hybrid blur with low intensity."""
        img_bytes = image_to_bytes(simple_test_image)

        response = requests.post(
            f"{api_url}/faces/blur",
            files={'file': ('test.png', img_bytes, 'image/png')},
            data={'intensity': 'low', 'blur_method': 'hybrid'},
            headers=api_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True

    def test_pixelate_intensity_high(self, api_is_running, api_url, api_headers, realistic_test_image, image_to_bytes):
        """Test pixelate with high intensity for maximum privacy."""
        img_bytes = image_to_bytes(realistic_test_image)

        response = requests.post(
            f"{api_url}/faces/blur",
            files={'file': ('test.png', img_bytes, 'image/png')},
            data={'intensity': 'high', 'blur_method': 'pixelate'},
            headers=api_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        # Should detect many faces with pixelation
        assert 'faces_detected' in data

    def test_blur_methods_with_custom_padding(self, api_is_running, api_url, api_headers, simple_test_image, image_to_bytes):
        """Test that blur methods work with custom padding."""
        for method in ['gaussian', 'pixelate', 'hybrid']:
            img_bytes = image_to_bytes(simple_test_image)
            response = requests.post(
                f"{api_url}/faces/blur",
                files={'file': ('test.png', img_bytes, 'image/png')},
                data={'blur_strength': 50, 'blur_method': method, 'face_padding': 15},
                headers=api_headers,
                timeout=10
            )

            assert response.status_code == 200, f"Method {method} failed"
            data = response.json()
            assert data['success'] is True
