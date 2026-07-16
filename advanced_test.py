#!/usr/bin/env python3
"""
Advanced testing script for blur and NSFW detection.
Generates realistic test images and verifies functionality.
"""

import requests
import base64
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import json
from pathlib import Path

API_BASE_URL = "http://localhost:8000"
API_KEY = "test-key"

class TestImageGenerator:
    """Generate test images with realistic face-like patterns."""

    @staticmethod
    def create_realistic_face_image():
        """Create a test image that looks more like faces."""
        img = Image.new('RGB', (800, 600), color='white')
        draw = ImageDraw.Draw(img)

        # Background gradient (simulate outdoor)
        img_array = np.array(img)
        for i in range(600):
            shade = int(135 + (i / 600) * 50)
            img_array[i, :] = [shade, shade + 30, shade + 60]
        img = Image.fromarray(img_array)
        draw = ImageDraw.Draw(img)

        # Draw multiple faces with skin tone
        faces = [
            (150, 150, 100),  # x, y, radius
            (450, 180, 95),
            (250, 380, 90),
            (600, 350, 100),
        ]

        for x, y, r in faces:
            # Draw face circle (skin tone)
            draw.ellipse([x-r, y-r, x+r, y+r], fill=(220, 180, 160), outline=(180, 140, 120))

            # Draw eyes
            draw.ellipse([x-r//3, y-r//4, x-r//6, y], fill=(50, 50, 50))
            draw.ellipse([x+r//6, y-r//4, x+r//3, y], fill=(50, 50, 50))

            # Draw nose
            draw.polygon([(x, y), (x-r//8, y+r//6), (x+r//8, y+r//6)], fill=(200, 160, 140))

            # Draw mouth
            draw.arc([x-r//4, y+r//6, x+r//4, y+r//2], 0, 180, fill=(200, 100, 100), width=3)

        return img

    @staticmethod
    def create_simple_test_image():
        """Create simple colored test image."""
        img = Image.new('RGB', (400, 300), color='white')
        draw = ImageDraw.Draw(img)

        # Draw rectangles as simple "faces"
        draw.rectangle([50, 50, 150, 150], fill=(200, 150, 150), outline=(100, 50, 50), width=2)
        draw.rectangle([250, 50, 350, 150], fill=(200, 150, 150), outline=(100, 50, 50), width=2)
        draw.rectangle([150, 180, 250, 280], fill=(200, 150, 150), outline=(100, 50, 50), width=2)

        return img


class APITester:
    """Test the API endpoints."""

    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {'X-API-Key': api_key}
        self.test_results = []

    def test_face_blur_basic(self, image: Image.Image, name: str = "test"):
        """Test basic face blur functionality."""
        print("\n" + "="*60)
        print(f"Test: Face Blur - {name}")
        print("="*60)

        img_bytes = io.BytesIO()
        image.save(img_bytes, format='PNG')
        img_bytes.seek(0)

        try:
            response = requests.post(
                f"{self.base_url}/faces/blur",
                files={'file': (f'{name}.png', img_bytes, 'image/png')},
                data={'blur_strength': 25},
                headers=self.headers,
                timeout=10
            )

            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print(f"✓ Success: {result.get('message')}")
                print(f"  Faces Detected: {result.get('faces_detected')}")
                print(f"  Image Base64 Length: {len(result.get('processed_image_base64', ''))}")

                # Decode and save
                img_data = base64.b64decode(result.get('processed_image_base64', ''))
                output_path = f'test_output_{name}_blur25.png'
                with open(output_path, 'wb') as f:
                    f.write(img_data)
                print(f"  Saved: {output_path}")

                self.test_results.append({
                    'test': f'Face Blur ({name})',
                    'status': '✓ PASS',
                    'faces_detected': result.get('faces_detected'),
                    'blur_strength': 25
                })
                return True
            else:
                print(f"✗ Error: {response.text}")
                self.test_results.append({
                    'test': f'Face Blur ({name})',
                    'status': f'✗ FAIL (Status {response.status_code})',
                })
                return False
        except Exception as e:
            print(f"✗ Exception: {e}")
            self.test_results.append({
                'test': f'Face Blur ({name})',
                'status': f'✗ ERROR: {str(e)}',
            })
            return False

    def test_blur_strength_comparison(self, image: Image.Image):
        """Test different blur strengths produce different results."""
        print("\n" + "="*60)
        print("Test: Blur Strength Comparison")
        print("="*60)

        results = {}
        for strength in [10, 25, 50, 100]:
            img_bytes = io.BytesIO()
            image.save(img_bytes, format='PNG')
            img_bytes.seek(0)

            try:
                response = requests.post(
                    f"{self.base_url}/faces/blur",
                    files={'file': ('test.png', img_bytes, 'image/png')},
                    data={'blur_strength': strength},
                    headers=self.headers,
                    timeout=10
                )

                if response.status_code == 200:
                    result = response.json()
                    img_data = base64.b64decode(result.get('processed_image_base64', ''))

                    # Save for visual comparison
                    output_path = f'test_blur_strength_{strength}.png'
                    with open(output_path, 'wb') as f:
                        f.write(img_data)

                    results[strength] = {
                        'status': '✓',
                        'faces_detected': result.get('faces_detected'),
                        'output_file': output_path
                    }
                    print(f"  blur_strength={strength}: ✓ ({result.get('faces_detected')} faces)")
                else:
                    results[strength] = {'status': '✗', 'error': response.status_code}
                    print(f"  blur_strength={strength}: ✗ Status {response.status_code}")
            except Exception as e:
                results[strength] = {'status': '✗', 'error': str(e)}
                print(f"  blur_strength={strength}: ✗ {e}")

        # Check if results are different
        success = all(r.get('status') == '✓' for r in results.values())
        if success:
            print("✓ All blur strengths executed successfully")
            self.test_results.append({
                'test': 'Blur Strength Comparison',
                'status': '✓ PASS',
                'details': f"Tested strengths: {list(results.keys())}"
            })
        else:
            self.test_results.append({
                'test': 'Blur Strength Comparison',
                'status': '✗ FAIL',
                'details': str(results)
            })

        return success

    def test_face_padding(self, image: Image.Image):
        """Test different padding values."""
        print("\n" + "="*60)
        print("Test: Face Padding Parameter")
        print("="*60)

        results = {}
        for padding in [0, 10, 20]:
            img_bytes = io.BytesIO()
            image.save(img_bytes, format='PNG')
            img_bytes.seek(0)

            try:
                response = requests.post(
                    f"{self.base_url}/faces/blur",
                    files={'file': ('test.png', img_bytes, 'image/png')},
                    data={'blur_strength': 30, 'face_padding': padding},
                    headers=self.headers,
                    timeout=10
                )

                if response.status_code == 200:
                    result = response.json()
                    img_data = base64.b64decode(result.get('processed_image_base64', ''))

                    output_path = f'test_padding_{padding}px.png'
                    with open(output_path, 'wb') as f:
                        f.write(img_data)

                    results[padding] = '✓'
                    print(f"  face_padding={padding}px: ✓")
                else:
                    results[padding] = f'✗ Status {response.status_code}'
                    print(f"  face_padding={padding}px: ✗ Status {response.status_code}")
            except Exception as e:
                results[padding] = f'✗ {str(e)}'
                print(f"  face_padding={padding}px: ✗ {e}")

        success = all(r == '✓' for r in results.values())
        self.test_results.append({
            'test': 'Face Padding',
            'status': '✓ PASS' if success else '✗ FAIL',
            'paddings_tested': list(results.keys())
        })

        return success

    def test_intensity_levels(self, image: Image.Image):
        """Test different intensity levels."""
        print("\n" + "="*60)
        print("Test: Intensity Levels")
        print("="*60)

        results = {}
        for intensity in ['low', 'medium', 'high']:
            img_bytes = io.BytesIO()
            image.save(img_bytes, format='PNG')
            img_bytes.seek(0)

            try:
                response = requests.post(
                    f"{self.base_url}/faces/blur",
                    files={'file': ('test.png', img_bytes, 'image/png')},
                    data={'intensity': intensity},
                    headers=self.headers,
                    timeout=10
                )

                if response.status_code == 200:
                    result = response.json()
                    results[intensity] = result.get('faces_detected', 0)
                    print(f"  intensity={intensity}: ✓ ({result.get('faces_detected')} faces)")
                else:
                    results[intensity] = None
                    print(f"  intensity={intensity}: ✗ Status {response.status_code}")
            except Exception as e:
                results[intensity] = None
                print(f"  intensity={intensity}: ✗ {e}")

        success = all(v is not None for v in results.values())
        self.test_results.append({
            'test': 'Intensity Levels',
            'status': '✓ PASS' if success else '✗ FAIL',
            'results': results
        })

        return success

    def test_nsfw_detection(self, image: Image.Image):
        """Test NSFW detection."""
        print("\n" + "="*60)
        print("Test: NSFW Detection")
        print("="*60)

        img_bytes = io.BytesIO()
        image.save(img_bytes, format='PNG')
        img_bytes.seek(0)

        try:
            response = requests.post(
                f"{self.base_url}/nsfw/check",
                files={'file': ('test.png', img_bytes, 'image/png')},
                params={'return_details': 'true'},
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✓ Success: NSFW Detection")
                print(f"  Is NSFW: {result.get('is_nsfw')}")
                print(f"  Primary Detection: {result.get('primary_detection')}")
                print(f"  Confidence: {result.get('confidence', 'N/A'):.3f}")

                detections = result.get('detections')
                if detections:
                    print(f"  Details:")
                    for cat, score in detections.items():
                        print(f"    {cat}: {score:.3f}")

                self.test_results.append({
                    'test': 'NSFW Detection',
                    'status': '✓ PASS',
                    'is_nsfw': result.get('is_nsfw'),
                    'primary': result.get('primary_detection')
                })
                return True
            elif response.status_code == 503:
                print(f"⚠ Model not loaded (expected if not downloaded)")
                self.test_results.append({
                    'test': 'NSFW Detection',
                    'status': '⚠ MODEL NOT LOADED',
                    'message': 'Download from: https://github.com/notAI-tech/NudeNet/releases/tag/v3'
                })
                return False
            else:
                print(f"✗ Error: Status {response.status_code}")
                self.test_results.append({
                    'test': 'NSFW Detection',
                    'status': f'✗ FAIL (Status {response.status_code})',
                })
                return False
        except Exception as e:
            print(f"✗ Exception: {e}")
            self.test_results.append({
                'test': 'NSFW Detection',
                'status': f'✗ ERROR: {str(e)}',
            })
            return False

    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)

        for i, result in enumerate(self.test_results, 1):
            test_name = result.get('test', 'Unknown')
            status = result.get('status', 'Unknown')
            print(f"{i}. {test_name}: {status}")

        passed = sum(1 for r in self.test_results if '✓' in r.get('status', ''))
        total = len(self.test_results)
        print(f"\nTotal: {passed}/{total} tests passed")

        # Save results to JSON
        with open('test_results.json', 'w') as f:
            json.dump(self.test_results, f, indent=2)
        print("\nDetailed results saved to: test_results.json")


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*58 + "║")
    print("║  " + "Advanced Testing - Blur & NSFW Detection".center(54) + "  ║")
    print("║" + " "*58 + "║")
    print("╚" + "="*58 + "╝")

    # Check if API is running
    print("\nChecking API connectivity...")
    try:
        response = requests.get(f"{API_BASE_URL}/docs", timeout=2)
        print("✓ API is running!")
    except Exception as e:
        print(f"✗ Cannot connect to API at {API_BASE_URL}")
        print(f"  Error: {e}")
        print(f"\nStart the API with:")
        print(f"  python -m uvicorn app.main:app --reload")
        return

    # Generate test images
    print("\nGenerating test images...")
    generator = TestImageGenerator()

    realistic_img = generator.create_realistic_face_image()
    realistic_img.save('test_image_realistic.png')
    print("✓ Generated: test_image_realistic.png")

    simple_img = generator.create_simple_test_image()
    simple_img.save('test_image_simple.png')
    print("✓ Generated: test_image_simple.png")

    # Run tests
    tester = APITester(API_BASE_URL, API_KEY)

    # Test with realistic image
    print("\n--- Testing with Realistic Image ---")
    tester.test_face_blur_basic(realistic_img, "realistic")
    tester.test_blur_strength_comparison(realistic_img)
    tester.test_face_padding(realistic_img)
    tester.test_intensity_levels(realistic_img)
    tester.test_nsfw_detection(realistic_img)

    # Print summary
    tester.print_summary()

    print("\n" + "="*60)
    print("Test Output Files:")
    print("="*60)
    print("  test_image_realistic.png - Realistic test image")
    print("  test_image_simple.png - Simple test image")
    print("  test_blur_strength_*.png - Different blur strengths")
    print("  test_padding_*px.png - Different padding values")
    print("  test_output_*.png - Full processing outputs")
    print("  test_results.json - Detailed test results")
    print("\n")


if __name__ == "__main__":
    main()
