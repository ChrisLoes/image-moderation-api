"""
Pytest configuration and fixtures for E2E tests.
"""

import pytest
import os
import subprocess
import time
import requests
from pathlib import Path
from PIL import Image
import numpy as np
import io

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "test-key")


@pytest.fixture(scope="session")
def api_url():
    """Get API base URL."""
    return API_BASE_URL


@pytest.fixture(scope="session")
def api_key():
    """Get API key."""
    return API_KEY


@pytest.fixture(scope="session")
def api_is_running():
    """Check if API is running, retry a few times."""
    max_retries = 10
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            response = requests.get(f"{API_BASE_URL}/docs", timeout=2)
            if response.status_code == 200:
                print(f"\n✓ API is running at {API_BASE_URL}")
                return True
        except requests.exceptions.ConnectionError:
            if attempt < max_retries - 1:
                print(f"Waiting for API... (attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
            continue

    raise RuntimeError(f"API is not running at {API_BASE_URL}. Start it with: python -m uvicorn app.main:app")


@pytest.fixture
def api_headers(api_key):
    """Get API headers with auth."""
    return {'X-API-Key': api_key}


@pytest.fixture
def simple_test_image():
    """Create a simple test image with colored rectangles."""
    img = Image.new('RGB', (400, 300), color='white')
    pixels = img.load()

    # Draw some colored areas to simulate faces
    for x in range(50, 150):
        for y in range(50, 150):
            pixels[x, y] = (200, 150, 150)  # Skin tone

    for x in range(250, 350):
        for y in range(50, 150):
            pixels[x, y] = (200, 150, 150)

    for x in range(150, 250):
        for y in range(180, 280):
            pixels[x, y] = (200, 150, 150)

    return img


@pytest.fixture
def realistic_test_image():
    """Create a more realistic test image."""
    img = Image.new('RGB', (800, 600), color='white')
    img_array = np.array(img)

    # Simulate background
    for i in range(600):
        shade = int(135 + (i / 600) * 50)
        img_array[i, :] = [shade, shade + 30, shade + 60]

    img = Image.fromarray(img_array)
    pixels = img.load()

    # Draw face circles (skin tone)
    faces = [(150, 150, 80), (450, 180, 80), (250, 380, 75), (600, 350, 80)]

    for cx, cy, r in faces:
        for x in range(max(0, cx - r), min(800, cx + r)):
            for y in range(max(0, cy - r), min(600, cy + r)):
                dist = np.sqrt((x - cx)**2 + (y - cy)**2)
                if dist <= r:
                    pixels[x, y] = (220, 180, 160)  # Skin tone

    return img


@pytest.fixture
def image_to_bytes():
    """Utility to convert PIL Image to bytes."""
    def _convert(image: Image.Image) -> io.BytesIO:
        img_bytes = io.BytesIO()
        image.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        return img_bytes
    return _convert


@pytest.fixture
def compare_images():
    """Utility to compare two images."""
    def _compare(img1: Image.Image, img2: Image.Image) -> dict:
        arr1 = np.array(img1)
        arr2 = np.array(img2)

        if arr1.shape != arr2.shape:
            return {
                'are_same': False,
                'reason': 'Different shapes',
                'difference': None,
                'std_diff': None
            }

        difference = np.abs(arr1.astype(float) - arr2.astype(float)).mean()
        std_diff = np.abs(arr1.astype(float).std() - arr2.astype(float).std())

        return {
            'are_same': difference < 1.0,
            'reason': f'Difference: {difference:.2f}',
            'difference': difference,
            'std_diff': std_diff
        }

    return _compare


@pytest.fixture
def decode_base64_image():
    """Utility to decode base64 image."""
    def _decode(base64_str: str) -> Image.Image:
        import base64
        img_data = base64.b64decode(base64_str)
        return Image.open(io.BytesIO(img_data))
    return _decode
