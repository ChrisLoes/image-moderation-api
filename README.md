# MediaPipe NSFW Detection API

A high-performance REST API for image processing with two core features:
- **Face Detection & Blurring** using MediaPipe
- **NSFW Content Detection** using NudeNet v3 (ONNX Runtime)

All requests require API key authentication. The API exposes comprehensive OpenAPI/Swagger documentation.

## Features

✅ Face detection and blurring with configurable blur strength  
✅ NSFW content detection using NudeNet v3 (ONNX)  
✅ Adjustable confidence thresholds (configurable without restart)  
✅ Support for JPEG, PNG, GIF, WebP (8 MB, max 4000×4000 px)  
✅ API Key authentication (X-API-Key header)  
✅ OpenAPI/Swagger UI (`/docs`)  
✅ Comprehensive error handling  
✅ Docker-ready for easy deployment  

## Installation

### Requirements
- Python 3.11+
- Docker & Docker Compose (for containerized deployment)

### Local Setup

```bash
git clone https://github.com/yourusername/mediapipe-nsfw-api.git
cd mediapipe-nsfw-api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Download NudeNet v3 model (required for NSFW detection)
mkdir -p models
# Download from: https://github.com/notAI-tech/NudeNet/releases/tag/v3
# Place classifier_nsfw.onnx in models/ directory
```

### Run Locally

```bash
# Set API keys
export API_KEYS="your-secret-key-1,your-secret-key-2"

# Start server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Access Swagger UI: `http://localhost:8000/docs`

## Docker Deployment

### Build Image

```bash
docker build -t mediapipe-nsfw-api:latest .
```

### Run with Docker Compose

```bash
# Copy environment file
cp .env.example .env

# Edit .env with your API keys and settings
docker-compose up -d
```

### Manual Docker Run

```bash
docker run -d \
  --name mediapipe-nsfw-api \
  -p 8000:8000 \
  -e API_KEYS="your-api-key-1,your-api-key-2" \
  -e NSFW_THRESHOLD=0.6 \
  -e FACE_BLUR_STRENGTH=25 \
  mediapipe-nsfw-api:latest
```

Access Swagger UI: `http://localhost:8000/docs`

## Configuration

All settings can be configured via environment variables:

```env
# API Authentication
API_KEYS=key1,key2,key3

# Face Detection
FACE_BLUR_STRENGTH=25           # Blur kernel size (1-50)
FACE_DETECTION_CONFIDENCE=0.5   # Detection threshold (0.0-1.0)

# NSFW Detection
NSFW_THRESHOLD=0.6              # Classification threshold (0.0-1.0)

# Image Limits
MAX_FILE_SIZE=8388608           # 8 MB in bytes
MAX_IMAGE_WIDTH=4000
MAX_IMAGE_HEIGHT=4000

# Server
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=info
```

**Runtime Parameter Override**: You can override defaults per request:
- Blur endpoint: `blur_strength`, `confidence_threshold` query params
- NSFW endpoint: `threshold`, `return_details` query params

## API Endpoints

### Health Check
```bash
curl http://localhost:8000/health
```

### Blur Faces

**Endpoint**: `POST /faces/blur`

```bash
curl -X POST http://localhost:8000/faces/blur \
  -H "X-API-Key: your-api-key" \
  -F "file=@image.jpg" \
  -F "blur_strength=25" \
  -F "confidence_threshold=0.5"
```

**Response**:
```json
{
  "success": true,
  "message": "Successfully processed image and blurred 3 face(s)",
  "faces_detected": 3,
  "processed_image_base64": "..."
}
```

### Check NSFW Content

**Endpoint**: `POST /nsfw/check`

```bash
curl -X POST http://localhost:8000/nsfw/check \
  -H "X-API-Key: your-api-key" \
  -F "file=@image.jpg" \
  -F "threshold=0.6" \
  -F "return_details=true"
```

**Response**:
```json
{
  "success": true,
  "is_nsfw": false,
  "confidence": 0.12,
  "primary_detection": "safe",
  "detections": {
    "safe": 0.88,
    "partially_nude": 0.08,
    "nude": 0.04
  }
}
```

## Plesk Server Deployment

### Prerequisites
- Plesk with Docker extension installed
- SSH access to server
- Domain name or IP address

### Step 1: Prepare Image for Plesk

```bash
# Build image locally or on server
docker build -t mediapipe-nsfw-api:latest .

# Tag for registry (if using private registry)
docker tag mediapipe-nsfw-api:latest your-registry/mediapipe-nsfw-api:latest
docker push your-registry/mediapipe-nsfw-api:latest
```

### Step 2: Push to Registry (Optional)

For easier management, push to Docker Hub or private registry:

```bash
docker login
docker tag mediapipe-nsfw-api:latest yourusername/mediapipe-nsfw-api:latest
docker push yourusername/mediapipe-nsfw-api:latest
```

### Step 3: Deploy via Plesk

**Option A: Using Plesk UI**

1. Go to **Plesk Dashboard** → **Containers** (if available)
2. Click **Create Container**
3. Image: `yourusername/mediapipe-nsfw-api:latest`
4. Port mapping: `8000 → 8000`
5. Environment variables (add from `.env`):
   - `API_KEYS=your-key-1,your-key-2`
   - `NSFW_THRESHOLD=0.6`
   - etc.
6. Memory limit: 2-4 GB recommended
7. Click **Create**

**Option B: SSH Deployment**

```bash
ssh root@your-plesk-server

# SSH into server
cd /var/www/your-domain

# Create docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.8'
services:
  api:
    image: yourusername/mediapipe-nsfw-api:latest
    container_name: mediapipe-nsfw-api
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - API_KEYS=your-key-1,your-key-2
      - NSFW_THRESHOLD=0.6
      - FACE_BLUR_STRENGTH=25
    volumes:
      - ./logs:/app/logs
    deploy:
      resources:
        limits:
          memory: 3G
        reservations:
          memory: 2G
EOF

# Start container
docker-compose up -d

# View logs
docker-compose logs -f
```

### Step 4: Setup Reverse Proxy (Nginx in Plesk)

In **Plesk Dashboard**:

1. **Domains** → your domain
2. **Hosting Settings** → **Apache & Nginx**
3. Add Nginx rule:

```nginx
location / {
    proxy_pass http://localhost:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 300s;
    proxy_connect_timeout 75s;
}
```

Now API is accessible at: `https://your-domain.com`

### Step 5: SSL Certificate (Optional but Recommended)

1. **Domains** → your domain
2. **SSL/TLS Certificates**
3. Use Let's Encrypt or upload existing certificate

### Monitoring & Logs

```bash
# SSH into server
docker logs -f mediapipe-nsfw-api

# View container stats
docker stats mediapipe-nsfw-api

# Restart container
docker restart mediapipe-nsfw-api

# Check health
curl https://your-domain.com/health
```

## NudeNet v3 Model Setup

The NSFW detection requires the NudeNet v3 ONNX model:

1. Download from: https://github.com/notAI-tech/NudeNet/releases/tag/v3
2. Place `classifier_nsfw.onnx` in `models/` directory

```bash
mkdir -p models
# Download and extract
curl -L https://github.com/notAI-tech/NudeNet/releases/download/v3/classifier_nsfw.onnx \
  -o models/classifier_nsfw.onnx
```

For Docker: The model should be included in the image or mounted as volume:

```yaml
volumes:
  - ./models:/app/models
```

## Error Handling

| Code | Reason |
|------|--------|
| 400 | Invalid image format or dimensions |
| 401 | Missing/invalid API key |
| 413 | File too large (exceeds 8 MB) |
| 503 | NSFW model not loaded |

## Performance Tips

- **GPU Support**: ONNX Runtime supports GPU acceleration. Ensure CUDA/TensorRT installed.
- **Memory**: Allocate 2-4 GB RAM for optimal performance
- **Caching**: Consider frontend caching for repeated images
- **Batch Processing**: Current API handles single images; batch endpoint can be added if needed

## Roadmap

- [ ] Batch image processing endpoint
- [ ] WebSocket support for streaming
- [ ] Admin dashboard for stats/monitoring
- [ ] Custom model upload support
- [ ] Image redaction (mosaic, pixelate alternatives)

## Troubleshooting

### NSFW Model Not Loading
```
Error: models/classifier_nsfw.onnx not found
```
**Solution**: Download model and place in `models/` directory

### Out of Memory
```
docker: memory limit exceeded
```
**Solution**: Increase Docker memory allocation or process images sequentially

### Slow Inference
```
Takes >5s per image
```
**Solution**: Enable GPU support with TensorRT, or reduce image dimensions

## License

MIT

## Support

For issues, feature requests, or contributions, please open an issue on GitHub.
