# NSFW Model Auto-Download Setup

## Overview

The NSFW detection model (`classifier_nsfw.onnx`) is now automatically downloaded during Docker build. No manual setup required!

## How It Works

### Build Phase
1. When building the Docker image, `scripts/download_nsfw_model.py` runs automatically
2. Downloads the latest NudeNet v3 classifier from GitHub releases
3. Saves to `/app/models/classifier_nsfw.onnx` inside the container

### Runtime Fallback
If the model is missing at runtime (e.g., pulled from old cached image):
1. `entrypoint.sh` checks if the model exists
2. If missing, it attempts to download it at startup
3. Falls back to manual download instructions if automatic download fails

## Download Methods

The script supports multiple download methods with automatic fallback:

1. **Python urllib** (primary)
   - Cross-platform, built-in
   - Handles HTTP/HTTPS
   
2. **curl** (fallback 1)
   - If urllib fails, tries `curl`
   - Better handling of redirects

3. **wget** (fallback 2)  
   - If curl fails, tries `wget`
   - Good HTTPS support

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

### If download fails during build:

```bash
# Build still succeeds (model download is not critical)
# At runtime, the entrypoint will attempt download again

# Check if model was downloaded:
docker exec <container_id> ls -lh /app/models/
```

### Manual download (if automatic fails):

```bash
# Download directly
curl -L -o classifier_nsfw.onnx \
  https://github.com/notAI-tech/NudeNet/releases/download/v3/classifier_nsfw.onnx

# Copy to container
docker cp classifier_nsfw.onnx <container_id>:/app/models/

# Or mount volume
docker run -v $(pwd)/models:/app/models mediapipe-nsfw-api:latest
```

## Environment Variables

No new environment variables needed. The download is automatic.

### Optional (for advanced users):

```bash
# Skip dependency installation (if using pre-built image)
INSTALL_DEPS=false
```

## Performance Notes

- **First build**: ~5-10 minutes (includes model download)
- **Subsequent builds**: Much faster (Docker layer caching)
- **Runtime startup**: < 1s (model already cached)

## Model Information

- **Source**: [NudeNet v3](https://github.com/notAI-tech/NudeNet)
- **Filename**: `classifier_nsfw.onnx`
- **Size**: ~300 MB
- **Format**: ONNX (Open Neural Network Exchange)
- **Framework**: Compatible with ONNX Runtime

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

1. Build image with model included:
   ```bash
   docker build -t mediapipe-nsfw-api:v1.0.0 .
   ```

2. Push to registry:
   ```bash
   docker push your-registry/mediapipe-nsfw-api:v1.0.0
   ```

3. Deploy to production:
   ```bash
   docker run -p 8000:8000 \
     -e API_KEYS=prod-key-1,prod-key-2 \
     your-registry/mediapipe-nsfw-api:v1.0.0
   ```

The model will be bundled with the image, so no external downloads at runtime.
