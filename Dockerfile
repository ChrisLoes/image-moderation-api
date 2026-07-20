FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application and entrypoint
COPY app/ ./app/
COPY entrypoint.sh .
COPY scripts/download_nsfw_model.py ./scripts/
COPY scripts/download_mediapipe_models.py ./scripts/

# Make entrypoint executable, create logs and models directories
RUN chmod +x entrypoint.sh && mkdir -p logs models/mediapipe

# Download latest models before creating non-root user
# NSFW model is required for NSFW detection endpoint
RUN echo "Downloading NSFW model (required)..." && \
    python scripts/download_nsfw_model.py && \
    echo "✅ NSFW model downloaded successfully" || \
    (echo "⚠️  NSFW model download failed, will retry at runtime" && exit 0)

# MediaPipe models are loaded dynamically on first use
RUN echo "Downloading MediaPipe models (optional)..." && \
    timeout 300 python scripts/download_mediapipe_models.py || \
    echo "✅ MediaPipe models will be downloaded at runtime"

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Expose port
EXPOSE 8000

# Run application via entrypoint
ENTRYPOINT ["./entrypoint.sh"]
