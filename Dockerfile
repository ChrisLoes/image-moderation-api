FROM python:3.14-slim

WORKDIR /app

# Install system dependencies
# libegl1/libgles2: required by MediaPipe >= 0.10.30 (Tasks API), even on CPU
RUN apt-get update && apt-get install -y \
    libgl1 \
    libegl1 \
    libgles2 \
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
COPY scripts/download_models.py ./scripts/

# Make entrypoint executable, create logs and models directories
RUN chmod +x entrypoint.sh && mkdir -p logs models

# Download and verify all models (faces, nudity, gestures). The build fails if a model
# is missing - an image without models would silently return 503 or unblurred images.
ENV MODELS_DIR=/app/models
RUN python scripts/download_models.py

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
