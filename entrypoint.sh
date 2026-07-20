#!/bin/bash
set -e

echo "=== MediaPipe NSFW Detection API ==="
echo "Starting application..."

# Set MediaPipe cache directory to use pre-downloaded models
export MEDIAPIPE_HOME=/app/models/mediapipe
mkdir -p "$MEDIAPIPE_HOME"

# Install/update dependencies if required
if [ ! -d "venv" ] && [ "$INSTALL_DEPS" != "false" ]; then
    echo "Installing Python dependencies..."
    pip install --no-cache-dir -r requirements.txt
fi

# Check for NSFW model and download if missing
if [ ! -f "models/classifier_nsfw.onnx" ]; then
    echo "WARNING: NSFW model not found at models/classifier_nsfw.onnx"
    echo "Attempting to download latest model..."

    if [ -f "scripts/download_nsfw_model.py" ]; then
        python scripts/download_nsfw_model.py
        if [ -f "models/classifier_nsfw.onnx" ]; then
            echo "NSFW model downloaded successfully at runtime!"
        else
            echo "ERROR: Failed to download NSFW model at runtime"
            echo "Download manually from: https://github.com/notAI-tech/NudeNet/releases/tag/v3"
        fi
    fi
fi

# Check for MediaPipe models and download if missing
if [ ! -f "models/mediapipe/face_detection_full_range.tflite" ]; then
    echo "WARNING: MediaPipe face detection model not found"
    echo "Attempting to download latest model..."

    if [ -f "scripts/download_mediapipe_models.py" ]; then
        python scripts/download_mediapipe_models.py
        if [ -f "models/mediapipe/face_detection_full_range.tflite" ]; then
            echo "MediaPipe models downloaded successfully at runtime!"
        else
            echo "WARNING: Could not download MediaPipe models, using automatic download at startup"
        fi
    fi
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
