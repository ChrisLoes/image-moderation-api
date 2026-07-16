#!/usr/bin/env python3
"""
E2E Test Runner - Executes all E2E tests without pytest dependency.
"""

import sys
import os
import time
import subprocess
import requests
from pathlib import Path
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:8000"
API_KEY = "test-key"
API_PROCESS = None
TEST_RESULTS = {
    'passed': 0,
    'failed': 0,
    'skipped': 0,
    'errors': []
}


def log(message: str, level: str = "INFO"):
    """Log with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {level:8} | {message}")


def start_api():
    """Start the API server."""
    global API_PROCESS
    log("Starting API server...")

    try:
        # Check if API is already running
        response = requests.get(f"{API_BASE_URL}/docs", timeout=2)
        if response.status_code == 200:
            log("API is already running!", "INFO")
            return True
    except:
        pass

    try:
        API_PROCESS = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(Path.cwd())
        )
        log("API process started", "INFO")

        # Wait for API to be ready
        max_retries = 15
        for i in range(max_retries):
            try:
                response = requests.get(f"{API_BASE_URL}/docs", timeout=2)
                if response.status_code == 200:
                    log("API is ready!", "SUCCESS")
                    return True
            except:
                if i < max_retries - 1:
                    log(f"Waiting for API... ({i+1}/{max_retries})", "WAIT")
                    time.sleep(2)

        log("API did not start in time", "ERROR")
        return False
    except Exception as e:
        log(f"Failed to start API: {e}", "ERROR")
        return False


def stop_api():
    """Stop the API server."""
    global API_PROCESS
    if API_PROCESS:
        log("Stopping API server...", "INFO")
        API_PROCESS.terminate()
        try:
            API_PROCESS.wait(timeout=5)
        except subprocess.TimeoutExpired:
            API_PROCESS.kill()
        log("API stopped", "INFO")


def run_test(test_name: str, test_func) -> bool:
    """Run a single test."""
    try:
        test_func()
        log(f"✓ {test_name}", "PASS")
        TEST_RESULTS['passed'] += 1
        return True
    except AssertionError as e:
        log(f"✗ {test_name}: {e}", "FAIL")
        TEST_RESULTS['failed'] += 1
        TEST_RESULTS['errors'].append((test_name, str(e)))
        return False
    except Exception as e:
        log(f"✗ {test_name}: ERROR: {e}", "ERROR")
        TEST_RESULTS['failed'] += 1
        TEST_RESULTS['errors'].append((test_name, str(e)))
        return False


# ============================================================================
# BLUR E2E TESTS
# ============================================================================

def test_blur_basic():
    """Test basic face blur."""
    from PIL import Image
    import io
    import base64

    img = Image.new('RGB', (200, 200), color='white')
    for x in range(50, 150):
        for y in range(50, 150):
            img.putpixel((x, y), (200, 150, 150))

    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    response = requests.post(
        f"{API_BASE_URL}/faces/blur",
        files={'file': ('test.png', img_bytes, 'image/png')},
        headers={'X-API-Key': API_KEY},
        timeout=10
    )

    assert response.status_code == 200, f"Status {response.status_code}"
    data = response.json()
    assert data['success'] is True
    assert 'processed_image_base64' in data
    assert len(data['processed_image_base64']) > 0


def test_blur_response_structure():
    """Test blur response structure."""
    from PIL import Image
    import io

    img = Image.new('RGB', (200, 200), color='white')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    response = requests.post(
        f"{API_BASE_URL}/faces/blur",
        files={'file': ('test.png', img_bytes, 'image/png')},
        data={'blur_strength': 25},
        headers={'X-API-Key': API_KEY},
        timeout=10
    )

    assert response.status_code == 200
    data = response.json()

    required = ['success', 'message', 'faces_detected', 'processed_image_base64']
    for field in required:
        assert field in data, f"Missing field: {field}"

    assert isinstance(data['success'], bool)
    assert isinstance(data['faces_detected'], int)
    assert isinstance(data['processed_image_base64'], str)


def test_blur_strength_parameter():
    """Test blur strength parameter."""
    from PIL import Image
    import io

    results = {}
    for strength in [10, 50]:
        img = Image.new('RGB', (200, 200), color='white')
        for x in range(50, 150):
            for y in range(50, 150):
                img.putpixel((x, y), (200, 150, 150))

        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)

        response = requests.post(
            f"{API_BASE_URL}/faces/blur",
            files={'file': ('test.png', img_bytes, 'image/png')},
            data={'blur_strength': strength},
            headers={'X-API-Key': API_KEY},
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        results[strength] = data['processed_image_base64']

    # Results should be different
    assert results[10] != results[50], "Different blur strengths should produce different results"


def test_blur_padding_parameter():
    """Test face padding parameter."""
    from PIL import Image
    import io

    results = {}
    for padding in [0, 20]:
        img = Image.new('RGB', (200, 200), color='white')
        for x in range(50, 150):
            for y in range(50, 150):
                img.putpixel((x, y), (200, 150, 150))

        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)

        response = requests.post(
            f"{API_BASE_URL}/faces/blur",
            files={'file': ('test.png', img_bytes, 'image/png')},
            data={'blur_strength': 30, 'face_padding': padding},
            headers={'X-API-Key': API_KEY},
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        results[padding] = data['processed_image_base64']

    # Results should be different
    assert results[0] != results[20], "Different padding should produce different results"


def test_blur_intensity_levels():
    """Test intensity levels."""
    from PIL import Image
    import io

    intensity_results = {}
    for intensity in ['low', 'medium', 'high']:
        img = Image.new('RGB', (300, 300), color='white')
        # Add more face-like areas for better detection with all intensities
        for i in range(4):
            for x in range(50 + i*70, 120 + i*70):
                for y in range(50, 120):
                    img.putpixel((x, y), (200, 150, 150))

        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)

        response = requests.post(
            f"{API_BASE_URL}/faces/blur",
            files={'file': ('test.png', img_bytes, 'image/png')},
            data={'intensity': intensity},
            headers={'X-API-Key': API_KEY},
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        intensity_results[intensity] = data['faces_detected']

    # All should have responses
    assert all(isinstance(v, int) for v in intensity_results.values())


def test_blur_missing_api_key():
    """Test blur without API key."""
    from PIL import Image
    import io

    img = Image.new('RGB', (200, 200), color='white')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    response = requests.post(
        f"{API_BASE_URL}/faces/blur",
        files={'file': ('test.png', img_bytes, 'image/png')},
        timeout=10
    )

    assert response.status_code == 401, f"Expected 401, got {response.status_code}"


def test_blur_invalid_image():
    """Test blur with invalid image."""
    response = requests.post(
        f"{API_BASE_URL}/faces/blur",
        files={'file': ('test.txt', b'not an image', 'text/plain')},
        headers={'X-API-Key': API_KEY},
        timeout=10
    )

    assert response.status_code in [400, 422], f"Expected 400 or 422, got {response.status_code}"


# ============================================================================
# NSFW E2E TESTS
# ============================================================================

def test_nsfw_basic():
    """Test basic NSFW detection."""
    from PIL import Image
    import io

    img = Image.new('RGB', (200, 200), color='blue')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    response = requests.post(
        f"{API_BASE_URL}/nsfw/check",
        files={'file': ('test.png', img_bytes, 'image/png')},
        headers={'X-API-Key': API_KEY},
        timeout=10
    )

    # Either 200 (model loaded) or 503 (model not loaded)
    assert response.status_code in [200, 503], f"Status {response.status_code}"

    if response.status_code == 200:
        data = response.json()
        assert data['success'] is True


def test_nsfw_response_structure():
    """Test NSFW response structure."""
    from PIL import Image
    import io

    img = Image.new('RGB', (200, 200), color='green')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    response = requests.post(
        f"{API_BASE_URL}/nsfw/check",
        files={'file': ('test.png', img_bytes, 'image/png')},
        headers={'X-API-Key': API_KEY},
        timeout=10
    )

    if response.status_code == 503:
        log("NSFW model not loaded (skipping detail tests)", "SKIP")
        TEST_RESULTS['skipped'] += 1
        return

    assert response.status_code == 200
    data = response.json()

    required = ['success', 'is_nsfw', 'confidence', 'primary_detection']
    for field in required:
        assert field in data, f"Missing field: {field}"

    assert isinstance(data['is_nsfw'], bool)
    assert 0.0 <= data['confidence'] <= 1.0
    assert data['primary_detection'] in ['safe', 'partially_nude', 'nude']


def test_nsfw_with_details():
    """Test NSFW with return_details."""
    from PIL import Image
    import io

    img = Image.new('RGB', (200, 200), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    response = requests.post(
        f"{API_BASE_URL}/nsfw/check",
        files={'file': ('test.png', img_bytes, 'image/png')},
        params={'return_details': 'true'},
        headers={'X-API-Key': API_KEY},
        timeout=10
    )

    if response.status_code == 503:
        log("NSFW model not loaded (skipping)", "SKIP")
        TEST_RESULTS['skipped'] += 1
        return

    assert response.status_code == 200
    data = response.json()

    assert 'detections' in data
    if data.get('detections'):
        categories = ['safe', 'partially_nude', 'nude']
        for cat in categories:
            assert cat in data['detections'], f"Missing category: {cat}"
            assert 0.0 <= data['detections'][cat] <= 1.0


def test_nsfw_missing_api_key():
    """Test NSFW without API key."""
    from PIL import Image
    import io

    img = Image.new('RGB', (200, 200), color='white')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    response = requests.post(
        f"{API_BASE_URL}/nsfw/check",
        files={'file': ('test.png', img_bytes, 'image/png')},
        timeout=10
    )

    assert response.status_code == 401, f"Expected 401, got {response.status_code}"


def test_nsfw_invalid_image():
    """Test NSFW with invalid image."""
    response = requests.post(
        f"{API_BASE_URL}/nsfw/check",
        files={'file': ('test.txt', b'not an image', 'text/plain')},
        headers={'X-API-Key': API_KEY},
        timeout=10
    )

    assert response.status_code in [400, 422], f"Expected 400 or 422, got {response.status_code}"


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*58 + "║")
    print("║  " + "E2E Test Suite - Blur & NSFW Detection".center(54) + "  ║")
    print("║" + " "*58 + "║")
    print("╚" + "="*58 + "╝\n")

    # Start API
    if not start_api():
        log("Cannot start API. Exiting.", "ERROR")
        return 1

    try:
        # BLUR TESTS
        print("\n" + "="*60)
        print("BLUR ENDPOINT TESTS")
        print("="*60 + "\n")

        run_test("test_blur_basic", test_blur_basic)
        run_test("test_blur_response_structure", test_blur_response_structure)
        run_test("test_blur_strength_parameter", test_blur_strength_parameter)
        run_test("test_blur_padding_parameter", test_blur_padding_parameter)
        run_test("test_blur_intensity_levels", test_blur_intensity_levels)
        run_test("test_blur_missing_api_key", test_blur_missing_api_key)
        run_test("test_blur_invalid_image", test_blur_invalid_image)

        # NSFW TESTS
        print("\n" + "="*60)
        print("NSFW ENDPOINT TESTS")
        print("="*60 + "\n")

        run_test("test_nsfw_basic", test_nsfw_basic)
        run_test("test_nsfw_response_structure", test_nsfw_response_structure)
        run_test("test_nsfw_with_details", test_nsfw_with_details)
        run_test("test_nsfw_missing_api_key", test_nsfw_missing_api_key)
        run_test("test_nsfw_invalid_image", test_nsfw_invalid_image)

        # SUMMARY
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60 + "\n")

        total = TEST_RESULTS['passed'] + TEST_RESULTS['failed'] + TEST_RESULTS['skipped']
        print(f"Total Tests:  {total}")
        print(f"Passed:       {TEST_RESULTS['passed']} ✓")
        print(f"Failed:       {TEST_RESULTS['failed']} ✗")
        print(f"Skipped:      {TEST_RESULTS['skipped']} ⊘")

        if TEST_RESULTS['errors']:
            print("\n" + "="*60)
            print("ERRORS")
            print("="*60 + "\n")
            for test_name, error in TEST_RESULTS['errors']:
                print(f"✗ {test_name}:")
                print(f"  {error}\n")

        success = TEST_RESULTS['failed'] == 0
        exit_code = 0 if success else 1

        print("\n" + ("="*60))
        if success:
            print("✓ ALL TESTS PASSED!")
        else:
            print("✗ SOME TESTS FAILED!")
        print("="*60 + "\n")

        return exit_code

    finally:
        stop_api()


if __name__ == "__main__":
    sys.exit(main())
