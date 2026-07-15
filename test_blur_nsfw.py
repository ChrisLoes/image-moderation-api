#!/usr/bin/env python3
"""
Test script to verify blur and NSFW detection functionality.
Creates a test image and tests both endpoints.
"""

import requests
import base64
import cv2
import numpy as np
from PIL import Image
import io

# Configuration
API_BASE_URL = "http://localhost:8000"
API_KEY = "test-key"

def create_test_image_with_faces():
    """Create a test image with some shapes representing faces."""
    # Create a 400x400 white image
    img = Image.new('RGB', (400, 400), color='white')
    img_array = np.array(img)

    # Add some colored rectangles to simulate faces
    # Face 1 - top left
    img_array[50:150, 50:150] = [200, 150, 150]  # Skin-like color
    # Add circle for face (simple representation)
    cv2.circle(img_array, (100, 100), 40, (255, 200, 180), -1)

    # Face 2 - top right
    img_array[50:150, 250:350] = [200, 150, 150]
    cv2.circle(img_array, (300, 100), 40, (255, 200, 180), -1)

    # Face 3 - bottom center
    img_array[250:350, 150:250] = [200, 150, 150]
    cv2.circle(img_array, (200, 300), 40, (255, 200, 180), -1)

    return Image.fromarray(img_array)

def test_face_blur():
    """Test face blur functionality."""
    print("\n" + "="*60)
    print("Testing Face Blur")
    print("="*60)

    # Create test image
    test_image = create_test_image_with_faces()

    # Convert to bytes
    img_bytes = io.BytesIO()
    test_image.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    # Test 1: Basic blur
    print("\n1. Testing basic blur (blur_strength=25)...")
    files = {'file': ('test.png', img_bytes, 'image/png')}
    headers = {'X-API-Key': API_KEY}
    data = {'blur_strength': 25}

    try:
        response = requests.post(f"{API_BASE_URL}/faces/blur", files=files, data=data, headers=headers)
        print(f"   Status Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"   ✓ Success: {result.get('message')}")
            print(f"   Faces Detected: {result.get('faces_detected')}")
            print(f"   Image Base64 Length: {len(result.get('processed_image_base64', ''))}")

            # Decode and save for visual inspection
            img_data = base64.b64decode(result.get('processed_image_base64', ''))
            with open('test_blur_output_weak.png', 'wb') as f:
                f.write(img_data)
            print(f"   Saved to: test_blur_output_weak.png")
        else:
            print(f"   ✗ Error: {response.text}")
    except Exception as e:
        print(f"   ✗ Connection Error: {e}")
        print(f"   Make sure API is running on {API_BASE_URL}")
        return

    # Test 2: Strong blur
    print("\n2. Testing strong blur (blur_strength=100)...")
    img_bytes.seek(0)
    files = {'file': ('test.png', img_bytes, 'image/png')}
    data = {'blur_strength': 100}

    try:
        response = requests.post(f"{API_BASE_URL}/faces/blur", files=files, data=data, headers=headers)
        print(f"   Status Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"   ✓ Success: {result.get('message')}")
            print(f"   Faces Detected: {result.get('faces_detected')}")

            # Decode and save for visual inspection
            img_data = base64.b64decode(result.get('processed_image_base64', ''))
            with open('test_blur_output_strong.png', 'wb') as f:
                f.write(img_data)
            print(f"   Saved to: test_blur_output_strong.png")
        else:
            print(f"   ✗ Error: {response.text}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 3: Different intensities
    print("\n3. Testing intensity levels...")
    for intensity in ['low', 'medium', 'high']:
        img_bytes.seek(0)
        files = {'file': ('test.png', img_bytes, 'image/png')}
        data = {'intensity': intensity}

        try:
            response = requests.post(f"{API_BASE_URL}/faces/blur", files=files, data=data, headers=headers)
            if response.status_code == 200:
                result = response.json()
                print(f"   ✓ {intensity.upper()}: {result.get('faces_detected')} faces detected")
            else:
                print(f"   ✗ {intensity.upper()}: Error {response.status_code}")
        except Exception as e:
            print(f"   ✗ {intensity.upper()}: {e}")

    # Test 4: Different padding values
    print("\n4. Testing padding values...")
    for padding in [0, 10, 20]:
        img_bytes.seek(0)
        files = {'file': ('test.png', img_bytes, 'image/png')}
        data = {'blur_strength': 25, 'face_padding': padding}

        try:
            response = requests.post(f"{API_BASE_URL}/faces/blur", files=files, data=data, headers=headers)
            if response.status_code == 200:
                result = response.json()
                print(f"   ✓ Padding {padding}px: {result.get('faces_detected')} faces detected")
            else:
                print(f"   ✗ Padding {padding}px: Error {response.status_code}")
        except Exception as e:
            print(f"   ✗ Padding {padding}px: {e}")

def test_nsfw_detection():
    """Test NSFW detection functionality."""
    print("\n" + "="*60)
    print("Testing NSFW Detection")
    print("="*60)

    # Create test image
    test_image = create_test_image_with_faces()

    # Convert to bytes
    img_bytes = io.BytesIO()
    test_image.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    # Test 1: Basic NSFW check
    print("\n1. Testing NSFW detection (default threshold)...")
    files = {'file': ('test.png', img_bytes, 'image/png')}
    headers = {'X-API-Key': API_KEY}

    try:
        response = requests.post(f"{API_BASE_URL}/nsfw/check", files=files, headers=headers)
        print(f"   Status Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"   ✓ Success")
            print(f"   Is NSFW: {result.get('is_nsfw')}")
            print(f"   Primary Detection: {result.get('primary_detection')}")
            print(f"   Confidence: {result.get('confidence'):.3f}")
        elif response.status_code == 503:
            print(f"   ⚠ Warning: NSFW model not loaded")
            print(f"   Message: {response.json().get('detail')}")
            print(f"   Download model from: https://github.com/notAI-tech/NudeNet/releases/tag/v3")
        else:
            print(f"   ✗ Error: {response.text}")
    except Exception as e:
        print(f"   ✗ Connection Error: {e}")
        print(f"   Make sure API is running on {API_BASE_URL}")
        return

    # Test 2: NSFW with details
    print("\n2. Testing NSFW detection with details...")
    img_bytes.seek(0)
    files = {'file': ('test.png', img_bytes, 'image/png')}

    try:
        response = requests.post(f"{API_BASE_URL}/nsfw/check", files=files, headers=headers, params={'return_details': 'true'})
        if response.status_code == 200:
            result = response.json()
            print(f"   ✓ Success")
            detections = result.get('detections')
            if detections:
                for category, score in detections.items():
                    print(f"   {category.capitalize()}: {score:.3f}")
        elif response.status_code == 503:
            print(f"   ⚠ NSFW model not loaded (expected if model not downloaded)")
        else:
            print(f"   ✗ Error: {response.text}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 3: Different intensities
    print("\n3. Testing intensity levels...")
    for intensity in ['low', 'medium', 'high']:
        img_bytes.seek(0)
        files = {'file': ('test.png', img_bytes, 'image/png')}

        try:
            response = requests.post(f"{API_BASE_URL}/nsfw/check", files=files, headers=headers, params={'intensity': intensity})
            if response.status_code == 200:
                result = response.json()
                print(f"   ✓ {intensity.upper()}: is_nsfw={result.get('is_nsfw')}, confidence={result.get('confidence'):.3f}")
            elif response.status_code == 503:
                print(f"   ⚠ {intensity.upper()}: Model not loaded")
            else:
                print(f"   ✗ {intensity.upper()}: Error {response.status_code}")
        except Exception as e:
            print(f"   ✗ {intensity.upper()}: {e}")

def main():
    """Run all tests."""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*58 + "║")
    print("║  " + "Testing Blur & NSFW Detection API".center(54) + "  ║")
    print("║" + " "*58 + "║")
    print("╚" + "="*58 + "╝")

    test_face_blur()
    test_nsfw_detection()

    print("\n" + "="*60)
    print("Test Complete")
    print("="*60)
    print("\nCheck the generated .png files for visual inspection of blur results:")
    print("  - test_blur_output_weak.png (blur_strength=25)")
    print("  - test_blur_output_strong.png (blur_strength=100)")
    print("\nNote: NSFW detection requires the model file at models/classifier_nsfw.onnx")
    print("Download from: https://github.com/notAI-tech/NudeNet/releases/tag/v3\n")

if __name__ == "__main__":
    main()
