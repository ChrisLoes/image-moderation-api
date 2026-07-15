#!/bin/bash
set -e

echo "=== MediaPipe NSFW Detection API ==="
echo "Starting application..."

# Install/update dependencies if required
if [ ! -d "venv" ] && [ "$INSTALL_DEPS" != "false" ]; then
    echo "Installing Python dependencies..."
    pip install --no-cache-dir -r requirements.txt
fi

# Check for required files
if [ ! -f "models/classifier_nsfw.onnx" ]; then
    echo "WARNING: NSFW model not found at models/classifier_nsfw.onnx"
    echo "NSFW detection will not be available until model is downloaded"
    echo "Download from: https://github.com/notAI-tech/NudeNet/releases/tag/v3"
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
