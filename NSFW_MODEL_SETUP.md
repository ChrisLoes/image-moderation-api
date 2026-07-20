# Model Auto-Download Setup

## Overview

Both the NSFW detection model (`classifier_nsfw.onnx`) and MediaPipe face detection models are now automatically downloaded during Docker build. No manual setup required!

## How It Works

### Build Phase (Two Models Downloaded)

**1. NSFW Detection Model**
- Script: `scripts/download_nsfw_model.py`
- Downloads latest NudeNet v3 classifier from GitHub releases
- Saves to `/app/models/classifier_nsfw.onnx` (~300 MB)

**2. MediaPipe Face Detection Model**
- Script: `scripts/download_mediapipe_models.py`
- Downloads full-range face detection model from Google Cloud Storage
- Saves to `/app/models/mediapipe/face_detection_full_range.tflite` (~40 MB)

### Runtime Fallback
If models are missing at runtime (e.g., pulled from old cached image):
1. `entrypoint.sh` checks for both models
2. If missing, it attempts to download them at startup
3. `MEDIAPIPE_HOME` environment variable points to cached models
4. Falls back to automatic download if manual download fails

## Download Methods

Both download scripts support multiple download methods with automatic fallback:

1. **Python urllib** (primary)
   - Cross-platform, built-in
   - Handles HTTP/HTTPS
   
2. **curl** (fallback 1)
   - If urllib fails, tries `curl`
   - Better handling of redirects

3. **wget** (fallback 2)  
   - If curl fails, tries `wget`
   - Good HTTPS support

## Models Downloaded

| Model | Source | Size | Type |
|-------|--------|------|------|
| `classifier_nsfw.onnx` | NudeNet v3 (GitHub) | ~300 MB | NSFW Detection |
| `face_detection_full_range.tflite` | MediaPipe (Google Cloud) | ~40 MB | Face Detection |
| **Total** | | **~340 MB** | Bundled in image |

## Building the Docker Image

```bash
# Build with automatic NSFW model download
docker build -t mediapipe-nsfw-api:latest .

# Run the container
docker run -p 8000:8000 \
  -e API_KEYS=your-api-key \
  mediapipe-nsfw-api:latest
```

The model will be ~300 MB and will be downloaded during build.

## Troubleshooting

### Check if models were downloaded:

```bash
# Inside container
docker exec <container_id> ls -lh /app/models/
docker exec <container_id> ls -lh /app/models/mediapipe/
```

### If downloads fail during build:

```bash
# Build still succeeds (models can be downloaded at runtime)
# At runtime, entrypoint will attempt download again

# Monitor build logs for errors:
docker build -t mediapipe-nsfw-api:latest . 2>&1 | grep -E "(Error|Warning|Downloaded)"
```

### Manual model setup (if automatic fails):

**For NSFW Model:**
```bash
# Download directly
curl -L -o classifier_nsfw.onnx \
  https://github.com/notAI-tech/NudeNet/releases/download/v3/classifier_nsfw.onnx

# Copy to container
docker cp classifier_nsfw.onnx <container_id>:/app/models/
```

**For MediaPipe Model:**
```bash
# Download directly
curl -L -o face_detection_full_range.tflite \
  https://storage.googleapis.com/mediapipe-assets/face_detection_full_range.tflite

# Copy to container
docker cp face_detection_full_range.tflite <container_id>:/app/models/mediapipe/
```

**Or mount models volume:**
```bash
docker run -p 8000:8000 \
  -v $(pwd)/models:/app/models \
  -e API_KEYS=your-key \
  mediapipe-nsfw-api:latest
```

### Verify models are working:

```bash
# Check Face Blur (should work regardless)
curl -X POST "http://localhost:8000/faces/blur" \
  -H "X-API-Key: your-key" \
  -F "file=@test_image.jpg" \
  -F "blur_strength=25"

# Check NSFW Detection (requires model)
curl -X POST "http://localhost:8000/nsfw/check" \
  -H "X-API-Key: your-key" \
  -F "file=@test_image.jpg"
```

## Environment Variables

No new environment variables needed. The download is automatic.

### Optional (for advanced users):

```bash
# Skip dependency installation (if using pre-built image)
INSTALL_DEPS=false
```

## Performance Notes

- **First build**: ~10-15 minutes (downloads both models, ~340 MB total)
- **Subsequent builds**: Much faster (Docker layer caching)
- **Container size**: +340 MB (models included in image)
- **Runtime startup**: < 500ms (models pre-loaded, no download needed)
- **First API request**: ~100-500ms (models initialized in memory)

**Benefits of pre-downloaded models:**
- No network calls at startup
- Consistent, reproducible deployments
- Faster response times
- Works in air-gapped environments

## Model Information

### NSFW Detection Model
- **Source**: [NudeNet v3](https://github.com/notAI-tech/NudeNet)
- **Filename**: `classifier_nsfw.onnx`
- **Size**: ~300 MB
- **Format**: ONNX (Open Neural Network Exchange)
- **Framework**: ONNX Runtime
- **Categories**: safe, partially_nude, nude

### Face Detection Model (MediaPipe)
- **Source**: [Google MediaPipe](https://github.com/google/mediapipe)
- **Filename**: `face_detection_full_range.tflite`
- **Size**: ~40 MB
- **Format**: TFLite (TensorFlow Lite)
- **Framework**: MediaPipe
- **Range**: Full-range (up to 5m away)
- **Output**: Bounding boxes + confidence scores

## Testing NSFW Endpoint

```bash
# Test NSFW detection
curl -X POST "http://localhost:8000/nsfw/check" \
  -H "X-API-Key: your-api-key" \
  -F "file=@test_image.jpg"

# Expected response (200 OK):
{
  "is_nsfw": false,
  "confidence": 0.95,
  "primary_detection": "safe",
  "detections": {
    "safe": 0.95,
    "partially_nude": 0.04,
    "nude": 0.01
  }
}
```

## Production Deployment

### 1. Build image with all models included:
```bash
docker build -t mediapipe-nsfw-api:v1.0.0 .
```

This will:
- Download NSFW model (~300 MB)
- Download MediaPipe face detection model (~40 MB)
- Bundle both into the image
- Set up environment variables

### 2. Push to registry:
```bash
# Tag for registry
docker tag mediapipe-nsfw-api:v1.0.0 your-registry/mediapipe-nsfw-api:v1.0.0

# Push image
docker push your-registry/mediapipe-nsfw-api:v1.0.0
```

### 3. Deploy to production:
```bash
docker run -d \
  --name nsfw-api \
  -p 8000:8000 \
  -e API_KEYS=prod-key-1,prod-key-2 \
  -e LOG_LEVEL=info \
  --restart=unless-stopped \
  your-registry/mediapipe-nsfw-api:v1.0.0
```

### 4. Verify deployment:
```bash
# Check health
curl http://localhost:8000/health

# Test face blur
curl -X POST "http://localhost:8000/faces/blur" \
  -H "X-API-Key: prod-key-1" \
  -F "file=@test_image.jpg"

# Test NSFW detection  
curl -X POST "http://localhost:8000/nsfw/check" \
  -H "X-API-Key: prod-key-1" \
  -F "file=@test_image.jpg"
```

### Advantages of bundled models:
- ✅ No model downloads at startup
- ✅ No external dependencies
- ✅ Consistent across all deployments
- ✅ Works in air-gapped environments
- ✅ ~340 MB image size (models included)
- ✅ Deterministic behavior
