#!/bin/bash
set -e

echo "=== MediaPipe NSFW Detection API ==="
echo "Starting application..."

# Install/update dependencies if required
if [ ! -d "venv" ] && [ "$INSTALL_DEPS" != "false" ]; then
    echo "Installing Python dependencies..."
    pip install --no-cache-dir -r requirements.txt
fi

# Make sure all models are present (normally baked into the image at build time)
export MODELS_DIR="${MODELS_DIR:-/app/models}"
if ! python scripts/download_models.py; then
    echo "WARNING: Some models could not be downloaded; they are retried on first use"
fi

# Log configuration
echo "Configuration:"
echo "  - Host: ${HOST:-0.0.0.0}"
echo "  - Port: ${PORT:-8000}"
echo "  - Log Level: ${LOG_LEVEL:-info}"
echo "  - Face Detection Intensity: ${FACE_DETECTION_INTENSITY:-medium}"
echo "  - NSFW Detection Intensity: ${NSFW_DETECTION_INTENSITY:-medium}"

echo "Starting Uvicorn server..."

# Run the application
exec uvicorn app.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}"
