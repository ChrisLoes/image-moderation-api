# E2E Testing Guide

## Overview

End-to-End (E2E) tests verify that the Face Blur and NSFW Detection APIs work correctly by making real HTTP requests and validating responses.

## Test Files

- **tests/conftest.py** - Pytest fixtures and configuration
- **tests/test_e2e_blur.py** - E2E tests for `/faces/blur` endpoint
- **tests/test_e2e_nsfw.py** - E2E tests for `/nsfw/check` endpoint
- **run_e2e_tests.py** - Standalone test runner (no pytest required)

## Running E2E Tests Locally

### Option 1: Using pytest (Recommended)

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Terminal 1: Start API
python -m uvicorn app.main:app --reload

# Terminal 2: Run tests
pytest tests/test_e2e_blur.py tests/test_e2e_nsfw.py -v --timeout=60
```

### Option 2: Using standalone runner

```bash
# Terminal 1: Start API
python -m uvicorn app.main:app --reload

# Terminal 2: Run tests (in background or new terminal)
python run_e2e_tests.py
```

## Test Coverage

### Face Blur E2E Tests

1. **test_blur_basic_success** - Verify basic blur request succeeds
2. **test_blur_response_structure** - Validate response has all required fields
3. **test_blur_strength_produces_different_results** - Different blur strengths produce different images
4. **test_blur_parameter_priority** - Explicit parameters override intensity
5. **test_blur_with_padding** - Different padding values produce different blur areas
6. **test_blur_intensity_levels** - Intensity levels (low/medium/high) are applied correctly
7. **test_blur_without_faces** - Handling images without detected faces
8. **test_blur_invalid_image_format** - Error handling for invalid image formats
9. **test_blur_missing_api_key** - Authentication validation
10. **test_blur_invalid_api_key** - Authorization validation
11. **test_blur_image_base64_is_valid** - Returned base64 image is valid
12. **test_blur_large_blur_strength** - Handling large blur strength values
13. **test_blur_zero_padding** - Handling zero padding

### NSFW Detection E2E Tests

1. **test_nsfw_basic_success** - Verify basic NSFW request succeeds
2. **test_nsfw_response_structure** - Validate response has all required fields
3. **test_nsfw_confidence_range** - Confidence score is between 0 and 1
4. **test_nsfw_primary_detection_valid** - Primary detection is a valid category
5. **test_nsfw_with_return_details** - Detailed detection scores are returned
6. **test_nsfw_without_return_details** - Details are not returned when not requested
7. **test_nsfw_intensity_levels** - Intensity levels are applied correctly
8. **test_nsfw_custom_threshold** - Custom threshold parameter works
9. **test_nsfw_invalid_image_format** - Error handling for invalid formats
10. **test_nsfw_missing_api_key** - Authentication validation
11. **test_nsfw_invalid_api_key** - Authorization validation
12. **test_nsfw_solid_color_image** - Handling solid color images
13. **test_nsfw_detections_sum_to_one** - Detection probabilities sum to 1.0

## Fixtures

### api_url
- Returns the API base URL (default: http://localhost:8000)
- Configurable via `API_BASE_URL` environment variable

### api_key
- Returns the API key for authentication
- Default: "test-key"
- Configurable via `API_KEY` environment variable

### api_is_running
- Verifies API is running and accessible
- Retries up to 10 times with 2-second delays
- Required for all E2E tests

### simple_test_image
- Creates a 400x300 test image with colored rectangles
- Simulates face regions
- Useful for basic blur testing

### realistic_test_image
- Creates an 800x600 test image with background gradient
- Includes multiple face-like circles
- Better for testing detection capabilities

### image_to_bytes
- Converts PIL Image to BytesIO for file upload
- Usage: `img_bytes = image_to_bytes(simple_test_image)`

### compare_images
- Compares two PIL Images
- Returns dict with: are_same, reason, difference, std_diff
- Usage: `comparison = compare_images(img1, img2)`

### decode_base64_image
- Decodes base64 string to PIL Image
- Usage: `img = decode_base64_image(response['processed_image_base64'])`

## Environment Variables

```bash
# API Configuration
export API_BASE_URL=http://localhost:8000
export API_KEY=test-key

# Run tests
pytest tests/test_e2e_*.py -v
```

## CI/CD Integration

E2E tests are automatically run in GitHub Actions:

1. **Unit Tests Pipeline** (.github/workflows/unit-tests.yml)
   - Runs existing unit tests
   - Checks code coverage

2. **E2E Tests Pipeline** (.github/workflows/e2e-tests.yml)
   - Runs E2E tests on push and pull requests
   - Daily scheduled runs
   - Supports both standard pytest and Docker environments

### View Test Results

1. Go to GitHub repository
2. Click "Actions" tab
3. Select "E2E Tests" workflow
4. View test results and artifacts

## Debugging Failed Tests

### Check API Logs

```bash
# Terminal with API
python -m uvicorn app.main:app --reload --log-level debug
```

### Verbose Test Output

```bash
pytest tests/test_e2e_*.py -v -s --tb=long
```

### Single Test Execution

```bash
pytest tests/test_e2e_blur.py::TestFaceBlurE2E::test_blur_basic_success -v -s
```

### Test Timeout Issues

Increase timeout (seconds):
```bash
pytest tests/ --timeout=120
```

## Expected Test Results

### Success
```
✓ All E2E tests passed
- Face Blur: 13/13 tests passing
- NSFW Detection: 13/13 tests passing
```

### Known Issues

**NSFW Model Not Loaded (503)**
- Expected if `models/classifier_nsfw.onnx` is not downloaded
- Download from: https://github.com/notAI-tech/NudeNet/releases/tag/v3
- Place in: `models/classifier_nsfw.onnx`

**Image Generation Tests Skip**
- Some image-based comparison tests may be skipped
- This is expected and not a failure

## Test Performance

Typical test execution time:
- Face Blur tests: ~30-45 seconds
- NSFW tests: ~20-30 seconds (or skipped if model not loaded)
- Total: ~50-75 seconds

## Continuous Integration Workflow

```
GitHub Push
    ↓
[Unit Tests] ← Run existing unit tests
    ↓
[E2E Tests] ← Run E2E tests against live API
    ↓
[Docker Build] ← Build and push Docker images
    ↓
✅ All checks pass → Ready to merge
```

## Troubleshooting

### "API is not running"
```bash
# Make sure API is started
python -m uvicorn app.main:app --reload
```

### "Connection refused"
```bash
# Check if API is accessible
curl http://localhost:8000/docs
```

### "Certificate verification failed"
```bash
# In CI/CD, ensure you're using HTTPS with valid certificates
# Or disable verification only in test environment
```

### "Test timeout"
```bash
# Increase timeout value
pytest --timeout=120
```

## Future Improvements

- [ ] Add performance benchmarking tests
- [ ] Add stress testing (concurrent requests)
- [ ] Add load testing
- [ ] Integrate with monitoring/alerting
- [ ] Add visual diff tests for blur comparison
- [ ] Add model update detection tests
