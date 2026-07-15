# Image Moderation API

<div align="center">

![GitHub Actions](https://github.com/ChrisLoes/image-moderation-api/actions/workflows/docker-test.yml/badge.svg)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![Docker Hub](https://img.shields.io/badge/docker%20hub-chrisloesleindocker-blue?logo=docker)
![License](https://img.shields.io/badge/license-MIT-green)

**Production-ready REST API for automated image moderation and face detection.**

Detect NSFW content and blur faces in images at scale. Built with FastAPI, MediaPipe, and NudeNet v3.

🐳 **Available on Docker Hub:** [`chrisloesleindocker/image-moderation-api`](https://hub.docker.com/r/chrisloesleindocker/image-moderation-api)

[🚀 Quick Start](#quick-start) • [📖 Documentation](#documentation) • [🔧 Configuration](#configuration) • [🐳 Docker Hub](#docker-deployment)

</div>

---

## Overview

A high-performance REST API for intelligent image moderation. Detect NSFW content, blur faces, and moderate user-generated content automatically.

**Perfect for:**
- 🎨 Content platforms & marketplaces
- 📱 Social media applications  
- 🛡️ User safety & compliance
- 🏢 Enterprise content filtering
- 👨‍💼 Corporate policy enforcement

---

## Features

### Core Capabilities
- 🔍 **NSFW Detection** - Classify images as safe/NSFW using NudeNet v3 (ONNX)
- 👤 **Face Detection & Blur** - Detect and blur faces using MediaPipe
- ⚡ **High Performance** - Optimized for low-latency, high-throughput processing
- 🔐 **Secure by Default** - API key authentication, request validation
- 📊 **Configurable** - Fine-tune sensitivity without code changes
- 🐳 **Docker Ready** - Containerized, production-grade deployment
- 📁 **Format Support** - JPEG, PNG, GIF, WebP, HEIF, HEIC (iPhone)
- 📈 **Comprehensive Logging** - Structured logs with request tracking
- 🔄 **Async Processing** - Non-blocking async handling with FastAPI

### Advanced Features
- 🎚️ **Intensity Levels** - Preset configurations (low/medium/high)
- 🔧 **Per-Request Overrides** - Fine-tune each request independently
- 📊 **Detailed Analytics** - Confidence scores and detailed breakdowns
- 🏥 **Health Checks** - Built-in service health monitoring
- 🔐 **Multi-Key Auth** - Support multiple API keys
- 📚 **Interactive Docs** - Swagger UI & ReDoc

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+ or Docker
- ~2-4 GB RAM

### ⚡ 60-Second Start (Docker Hub Only)

No git clone needed - just run:

```bash
# Pull and run the image (takes ~1-2 min on first run)
docker run -d -p 8000:8000 -e API_KEYS="test-key-1" chrisloesleindocker/image-moderation-api:latest

# Test it
curl http://localhost:8000/health

# Open Swagger UI in browser
# http://localhost:8000/docs (API Key: test-key-1)
```

Done! ✅

---

### 1. With Docker Hub (Easiest - No Clone Needed)

```bash
# Pull and run directly from Docker Hub
docker run -d \
  --name image-moderation \
  -p 8000:8000 \
  -e API_KEYS="test-key-1,test-key-2" \
  chrisloesleindocker/image-moderation-api:latest

# Check health
curl http://localhost:8000/health
```

**Or with Docker Compose:**
```bash
docker compose -f - up -d <<EOF
version: '3.8'
services:
  api:
    image: chrisloesleindocker/image-moderation-api:latest
    ports:
      - "8000:8000"
    environment:
      - API_KEYS=test-key-1,test-key-2
      - LOG_LEVEL=info
EOF
```

### 2. With Docker Compose (Clone Repository)

```bash
# Clone repository
git clone https://github.com/ChrisLoes/image-moderation-api.git
cd image-moderation-api

# Configure
cp .env.example .env
# Edit .env with your API keys

# Start
docker-compose up -d

# Access
curl http://localhost:8000/health
```

### 3. Local Installation

```bash
# Clone and setup
git clone https://github.com/ChrisLoes/image-moderation-api.git
cd image-moderation-api

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env

# Start
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Test the API

**Using Swagger UI:**
```
Open: http://localhost:8000/docs
Authorize with: test-key-1
Try any endpoint
```

**Using cURL:**
```bash
# Detect NSFW content
curl -X POST http://localhost:8000/nsfw/check \
  -H "X-API-Key: test-key-1" \
  -F "file=@image.jpg"

# Blur faces
curl -X POST http://localhost:8000/faces/blur \
  -H "X-API-Key: test-key-1" \
  -F "file=@image.jpg" \
  -F "intensity=high"
```

---

## API Endpoints

### 🏥 Health Check
```bash
GET /health
```
Check service health and readiness.

### 🚨 Detect NSFW Content
```bash
POST /nsfw/check
```

**Request:**
```bash
curl -X POST http://localhost:8000/nsfw/check \
  -H "X-API-Key: test-key-1" \
  -F "file=@image.jpg" \
  -F "intensity=high" \
  -F "return_details=true"
```

**Response:**
```json
{
  "success": true,
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

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `file` | File | required | Image file (JPEG, PNG, GIF, WebP, HEIF, HEIC) |
| `intensity` | String | medium | Detection level: `low`, `medium`, `high` |
| `threshold` | Float | - | Override threshold (0.0-1.0) |
| `return_details` | Boolean | false | Include all category scores |

---

### 👤 Blur Faces
```bash
POST /faces/blur
```

**Request:**
```bash
curl -X POST http://localhost:8000/faces/blur \
  -H "X-API-Key: test-key-1" \
  -F "file=@image.jpg" \
  -F "intensity=high"
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully blurred 3 face(s)",
  "faces_detected": 3,
  "processed_image_base64": "iVBORw0KGgoAAAA..."
}
```

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `file` | File | required | Image file |
| `intensity` | String | medium | Blur level: `low`, `medium`, `high` |
| `blur_strength` | Integer | - | Kernel size (1-50, must be odd) |
| `confidence_threshold` | Float | - | Detection sensitivity (0.0-1.0) |

---

## 🐳 Docker Deployment

### Option 1: Docker Hub (Recommended)

Pull the pre-built image from Docker Hub:

```bash
docker pull chrisloesleindocker/image-moderation-api:latest
docker run -d \
  --name image-moderation \
  -p 8000:8000 \
  -e API_KEYS="your-secret-key" \
  chrisloesleindocker/image-moderation-api:latest
```

**Available Tags:**
- `latest` - Latest stable version
- `v1.0` - Specific version tags

### Option 2: Using Docker Compose

With Docker Hub image (no clone needed):

```yaml
# docker-compose.yml
version: '3.8'
services:
  api:
    image: chrisloesleindocker/image-moderation-api:latest
    container_name: image-moderation-api
    ports:
      - "8000:8000"
    environment:
      - API_KEYS=your-secret-key-1,your-secret-key-2
      - LOG_LEVEL=info
      - FACE_DETECTION_INTENSITY=high
      - NSFW_DETECTION_INTENSITY=medium
    volumes:
      - ./models:/app/models
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

Start:
```bash
docker-compose up -d
```

### Option 3: Build Locally

Clone and build from source:

```bash
git clone https://github.com/ChrisLoes/image-moderation-api.git
cd image-moderation-api

# Build image
docker build -t image-moderation-api:latest .

# Run locally built image
docker run -d \
  -p 8000:8000 \
  -e API_KEYS="test-key" \
  image-moderation-api:latest

# Tag and push to your Docker Hub
docker tag image-moderation-api:latest chrisloesleindocker/image-moderation-api:latest
docker push chrisloesleindocker/image-moderation-api:latest
```

### Docker Hub Repository

Repository: [chrisloesleindocker/image-moderation-api](https://hub.docker.com/r/chrisloesleindocker/image-moderation-api)

**Pull Command:**
```bash
docker pull chrisloesleindocker/image-moderation-api:latest
```

**Image Size:** ~2.0 GB  
**Base Image:** Python 3.12-slim  
**Architecture:** linux/amd64

### Getting Updates

Keep your image up to date:

```bash
# Pull latest version
docker pull chrisloesleindocker/image-moderation-api:latest

# Recreate container with new image
docker-compose down
docker-compose up -d
```

### Pushing Your Own Image

If you build locally and want to push to Docker Hub:

```bash
# Login to Docker Hub
docker login

# Build image
docker build -t chrisloesleindocker/image-moderation-api:latest .

# Push to Docker Hub
docker push chrisloesleindocker/image-moderation-api:latest

# Tag a specific version
docker tag chrisloesleindocker/image-moderation-api:latest chrisloesleindocker/image-moderation-api:v1.0.0
docker push chrisloesleindocker/image-moderation-api:v1.0.0
```

---

## ⚙️ Configuration

All settings via environment variables (`.env` or Docker):

### API & Security
```env
API_KEYS=key1,key2,key3           # Comma-separated API keys
LOG_LEVEL=info                    # debug, info, warning, error
```

### Face Detection
```env
FACE_DETECTION_INTENSITY=medium   # low, medium, high
FACE_DETECTION_CONFIDENCE=0.5     # 0.0-1.0 (ignored if intensity set)
FACE_BLUR_STRENGTH=25             # 1-50, must be odd
```

### NSFW Detection
```env
NSFW_DETECTION_INTENSITY=medium   # low, medium, high
NSFW_THRESHOLD=0.6                # 0.0-1.0 (ignored if intensity set)
```

### Image Constraints
```env
MAX_FILE_SIZE=8388608             # 8 MB default
MAX_IMAGE_WIDTH=4000              # pixels
MAX_IMAGE_HEIGHT=4000             # pixels
```

### Intensity Levels

**Face Detection:**
| Level | Confidence | Blur | Use Case |
|-------|-----------|------|----------|
| low | 0.3 | 11px | Minimal privacy |
| medium | 0.5 | 25px | Balanced (recommended) |
| high | 0.8 | 41px | Maximum privacy |

**NSFW Detection:**
| Level | Threshold | Use Case |
|-------|-----------|----------|
| low | 0.8 | Lenient (user content) |
| medium | 0.6 | Balanced (recommended) |
| high | 0.4 | Strict (compliance) |

---

## 📚 Documentation

### Interactive API Docs

**Swagger UI (Try It Out):**
```
http://localhost:8000/docs
```

**ReDoc (Beautiful Docs):**
```
http://localhost:8000/redoc
```

**OpenAPI Schema:**
```
http://localhost:8000/openapi.json
```

### Complete Documentation

See [.github/WORKFLOWS.md](.github/WORKFLOWS.md) for CI/CD pipeline details.
See [CI_CD_SETUP.md](CI_CD_SETUP.md) for GitHub Actions setup.

---

## 🔄 CI/CD Pipeline

This project includes a **production-ready GitHub Actions CI/CD pipeline**:

### Automated Workflows
- ✅ **Unit Tests** - Python 3.10/3.11/3.12
- ✅ **Docker Build Tests** - Container health checks
- ✅ **Security Scanning** - Trivy vulnerability scan
- ✅ **Dependency Updates** - Automated with Dependabot
- ✅ **Auto-Fix** - Automatic fixes for common issues
- ✅ **AI Diagnostics** - Claude AI problem analysis
- ✅ **Docker Hub Push** - Automatic image publishing

### Getting Started with CI/CD
1. Fork repository
2. Add GitHub Secrets:
   - `DOCKERHUB_USERNAME`
   - `DOCKERHUB_TOKEN`
   - `ANTHROPIC_API_KEY` (optional, for AI diagnostics)
3. Push to main → Automated build & publish

See [CI_CD_SETUP.md](CI_CD_SETUP.md) for complete setup guide.

---

## 🔧 Environment Setup

### 1. Clone Repository
```bash
git clone https://github.com/ChrisLoes/image-moderation-api.git
cd image-moderation-api
```

### 2. Install NudeNet Model
```bash
mkdir -p models
curl -L https://github.com/notAI-tech/NudeNet/releases/download/v3/classifier_nsfw.onnx \
  -o models/classifier_nsfw.onnx
```

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env with your settings
nano .env
```

### 4. Start Service
```bash
# Option A: Docker Compose
docker-compose up -d

# Option B: Local Python
python -m uvicorn app.main:app --reload

# Option C: Using Gunicorn (Production)
gunicorn -w 4 -b 0.0.0.0:8000 app.main:app
```

---

## 📊 Logging

### Log Files
```
logs/
├── api.log       # All requests and operations
└── error.log     # Errors only
```

### View Logs
```bash
# Docker Compose
docker-compose logs -f api

# Docker
docker logs -f image-moderation

# Local
tail -f logs/api.log
```

### Log Levels
```bash
# Development
export LOG_LEVEL=debug

# Production
export LOG_LEVEL=info
```

---

## 🚀 Performance & Scaling

### System Requirements
| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| RAM | 2 GB | 4 GB |
| Disk | 1 GB | 5 GB |
| GPU | Optional | NVIDIA GPU (CUDA) |

### Performance Tips
- **GPU Support**: Enable CUDA/TensorRT for faster inference
- **Caching**: Cache results for identical images
- **Batch Processing**: Process multiple images in parallel
- **Load Balancing**: Run multiple containers behind load balancer

### Typical Performance
- Face Detection: ~200-500ms per image
- NSFW Detection: ~300-800ms per image
- Combined: ~500-1000ms per image

*Times vary based on image size, GPU availability, and system load*

---

## 🤝 Contributing

Contributions welcome! 

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

### Development Setup
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pytest tests/ -v
```

---

## 📋 Roadmap

- [ ] Batch processing endpoint
- [ ] WebSocket support for streaming
- [ ] Admin dashboard
- [ ] Custom model upload
- [ ] Alternative redaction modes (mosaic, pixelate)
- [ ] Redis caching layer
- [ ] Prometheus metrics export
- [ ] Multi-language support

---

## 🐛 Troubleshooting

### Model Not Found
```
Error: models/classifier_nsfw.onnx not found
```
**Solution:** Download NudeNet model to `models/` directory

### Out of Memory
```
Error: memory limit exceeded
```
**Solution:** Increase Docker memory or process images sequentially

### API Key Issues
```
Error: 401 Unauthorized
```
**Solution:** Check `X-API-Key` header and verify key in environment

### Slow Processing
```
Request takes >10 seconds
```
**Solution:** Enable GPU support, reduce image size, or check system load

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details

---

## 🙋 Support & Contact

- **Issues:** [GitHub Issues](https://github.com/ChrisLoes/image-moderation-api/issues)
- **Discussions:** [GitHub Discussions](https://github.com/ChrisLoes/image-moderation-api/discussions)
- **Email:** steffen.loeslein@googlemail.com

---

## 🙏 Acknowledgments

- [MediaPipe](https://mediapipe.dev/) - Face detection
- [NudeNet](https://github.com/notAI-tech/NudeNet) - NSFW classification
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [ONNX Runtime](https://onnxruntime.ai/) - Model inference

---

<div align="center">

Made with ❤️ by [Chris Loes](https://github.com/ChrisLoes)

⭐ If you find this project useful, please consider giving it a star!

</div>
