# Troubleshooting Guide

## Problem: Faces Not Detected (Images returned unchanged)

### Root Cause
The face detector was missing the `static_image_mode=True` parameter. This parameter tells MediaPipe to optimize for **static images** instead of video streams.

```python
# ✗ BROKEN (before fix)
detector = mp_face_detection.FaceDetection(
    model_selection=0,
    min_detection_confidence=threshold
)

# ✓ FIXED (after fix)
detector = mp_face_detection.FaceDetection(
    static_image_mode=True,  # CRITICAL for image processing
    model_selection=0,
    min_detection_confidence=threshold
)
```

### Why This Matters
- **Without `static_image_mode=True`**: Face detector is optimized for video streams and may fail or be unreliable on static images
- **With `static_image_mode=True`**: Face detector properly handles individual image frames and provides consistent results

---

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Verify Installation
```bash
python test_face_detection.py
```

### 3. Test the API

**Using curl:**
```bash
curl -X POST http://localhost:8000/faces/blur \
  -H "X-API-Key: test-key" \
  -F "file=@your_image.jpg" \
  -F "intensity=medium"
```

**Using Python:**
```python
import requests
from pathlib import Path

with open("your_image.jpg", "rb") as f:
    response = requests.post(
        "http://localhost:8000/faces/blur",
        files={"file": f},
        data={"intensity": "medium"},
        headers={"X-API-Key": "test-key"}
    )
    print(response.json())
```

---

## Debugging Checklist

If faces are still not being detected:

### 1. **Image Quality**
- ✓ Image has clear, frontal faces
- ✓ Faces are not too small (<20x20 pixels)
- ✓ Image has good lighting
- ✓ Face is not obscured (glasses, masks, etc.)

### 2. **Confidence Threshold**
Try lowering the threshold:

```bash
# Start with very lenient threshold (0.3)
curl -X POST http://localhost:8000/faces/blur \
  -H "X-API-Key: test-key" \
  -F "file=@your_image.jpg" \
  -F "confidence_threshold=0.3"

# Or use intensity=low (which sets threshold to 0.3)
curl -X POST http://localhost:8000/faces/blur \
  -H "X-API-Key: test-key" \
  -F "file=@your_image.jpg" \
  -F "intensity=low"
```

### 3. **Image Format**
Ensure your image is in a supported format:
- ✓ JPEG
- ✓ PNG  
- ✓ WebP
- ✓ GIF

### 4. **Check Logs**
```bash
# If running with Docker
docker logs <container_id>

# If running directly
# Check logs/ directory for api.log and error.log
tail -f logs/api.log
```

### 5. **Verify Response**
Check the `faces_detected` field in the response:

```python
# No faces detected
{"success": true, "faces_detected": 0, "processed_image_base64": "..."}

# Faces detected and blurred
{"success": true, "faces_detected": 2, "processed_image_base64": "..."}
```

---

## Parameter Priority

Remember the parameter priority when calling the API:

### For `/faces/blur`:
1. **Explicit `blur_strength`** (overrides everything)
2. **Explicit `confidence_threshold`** (overrides everything)
3. **`intensity` parameter** (low/medium/high)
4. **Environment defaults**

```bash
# This uses blur_strength=41, NOT the "low" intensity's value of 11
curl -X POST http://localhost:8000/faces/blur \
  -H "X-API-Key: test-key" \
  -F "file=@image.jpg" \
  -F "intensity=low" \
  -F "blur_strength=41"
```

---

## Model Selection

Two face detection models available:

| model_selection | Range | Speed | Use Case |
|---|---|---|---|
| **0** (default) | Short-range (<2m) | Fast | Mobile, close-ups |
| **1** | Full-range (5m) | Slower | Long-distance detection |

To use full-range model in code:
```python
detector = mp_face_detection.FaceDetection(
    static_image_mode=True,
    model_selection=1,  # Full-range model
    min_detection_confidence=0.5
)
```

---

## Performance Tips

1. **Use appropriate confidence threshold**
   - `0.3` = very lenient (slow, many false positives)
   - `0.5` = balanced (recommended)
   - `0.8` = strict (fast, fewer detections)

2. **Resize large images** before sending
   - Max 4000×4000 px (configured in settings)
   - For faster processing, resize to <2000×2000 px

3. **Use correct intensity level**
   - `low` (0.3): Quick pass, find obvious faces
   - `medium` (0.5): Balanced, default
   - `high` (0.8): Thorough, stricter

---

## Common Issues

| Issue | Cause | Solution |
|---|---|---|
| 503 error on `/nsfw/check` | Model file missing | Download from: https://github.com/notAI-tech/NudeNet/releases/tag/v3 |
| No faces detected | `static_image_mode` missing | Already fixed in latest version |
| Faces too small | Image resolution | Ensure faces are at least 20×20 pixels |
| API returns original image | No faces found | Lower `confidence_threshold` or check image quality |
| 422 validation error | Invalid parameter type | Check parameter types (threshold: float, blur_strength: int) |

---

## Testing

Run the test suite to verify everything is working:

```bash
# Run all tests
pytest tests/test_api.py -v

# Run only parameter validation tests
pytest tests/test_api.py::TestParameterApplication -v

# Run with coverage report
pytest tests/test_api.py --cov=app --cov-report=html
```
