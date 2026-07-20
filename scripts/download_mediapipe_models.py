#!/usr/bin/env python3
"""
Download MediaPipe face detection models for offline use.
Supports both short-range and full-range models.
"""

import os
import sys
import socket
import shutil
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

# Configuration
MEDIAPIPE_CACHE_DIR = Path.home() / ".mediapipe"
MODELS_DIR = Path("/app/models/mediapipe")

# MediaPipe model URLs from Google Cloud Storage
MODELS = {
    "face_detection_short_range.tflite": {
        "url": "https://storage.googleapis.com/mediapipe-assets/face_detection_short_range.tflite",
        "size_mb": 5.4,
        "description": "Short-range face detection (up to 2m)"
    },
    "face_detection_full_range.tflite": {
        "url": "https://storage.googleapis.com/mediapipe-assets/face_detection_full_range.tflite",
        "size_mb": 40.0,
        "description": "Full-range face detection (up to 5m)"
    },
    "face_landmarker.task": {
        "url": "https://storage.googleapis.com/mediapipe-assets/face_landmarker.task",
        "size_mb": 500.0,
        "description": "Face landmarks detector (optional)"
    }
}

def download_model(model_name, model_info):
    """Download a single MediaPipe model."""
    url = model_info["url"]
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODELS_DIR / model_name

    # Check if already exists
    if model_path.exists():
        file_size_mb = model_path.stat().st_size / (1024 * 1024)
        print(f"  ✓ Already exists: {model_name} ({file_size_mb:.1f} MB)")
        return True

    print(f"  Downloading: {model_name} ({model_info['size_mb']:.1f} MB)")
    print(f"  URL: {url}")

    try:
        # Try urllib first
        def download_progress(block_num, block_size, total_size):
            if total_size > 0:
                downloaded = block_num * block_size
                percent = min(downloaded * 100 // total_size, 100)
                mb_downloaded = downloaded / (1024 * 1024)
                mb_total = total_size / (1024 * 1024)
                print(f"    Progress: {percent}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)", end="\r")

        request = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        # Set timeout to 10 minutes for large downloads
        old_timeout = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(600)
            with urllib.request.urlopen(request) as response:
                with open(model_path, 'wb') as out_file:
                    shutil.copyfileobj(response, out_file)
            print()
        finally:
            socket.setdefaulttimeout(old_timeout)

        # Verify file
        if model_path.exists() and model_path.stat().st_size > 100000:  # At least 100KB
            file_size_mb = model_path.stat().st_size / (1024 * 1024)
            print(f"  ✓ Downloaded: {model_name} ({file_size_mb:.1f} MB)")
            return True
        else:
            raise FileNotFoundError(f"Downloaded file is too small or missing")

    except (urllib.error.URLError, FileNotFoundError) as e:
        print(f"  ! urllib failed: {e}")

        # Try curl as fallback
        try:
            print(f"  Trying curl...")
            result = subprocess.run(
                ["curl", "-L", "-o", str(model_path), url],
                capture_output=True,
                timeout=300
            )
            if result.returncode == 0 and model_path.exists() and model_path.stat().st_size > 100000:
                file_size_mb = model_path.stat().st_size / (1024 * 1024)
                print(f"  ✓ Downloaded with curl: {model_name} ({file_size_mb:.1f} MB)")
                return True
        except Exception as e:
            print(f"  ! curl failed: {e}")

        print(f"  ✗ Failed to download: {model_name}")
        return False

def main():
    """Main execution."""
    print("=" * 70)
    print("MediaPipe Model Downloader")
    print("=" * 70)

    # We only need full-range for our use case
    models_to_download = {
        "face_detection_full_range.tflite": MODELS["face_detection_full_range.tflite"]
    }

    print(f"\nTarget directory: {MODELS_DIR}")
    print(f"Cache directory: {MEDIAPIPE_CACHE_DIR}\n")

    success_count = 0
    for model_name, model_info in models_to_download.items():
        print(f"\n{model_name}")
        print(f"  {model_info['description']}")
        if download_model(model_name, model_info):
            success_count += 1

    print("\n" + "=" * 70)
    if success_count == len(models_to_download):
        print(f"Success! Downloaded {success_count}/{len(models_to_download)} models")
        return 0
    else:
        print(f"Partial success: {success_count}/{len(models_to_download)} models downloaded")
        print("\nNote: MediaPipe will automatically download missing models at first use")
        return 0  # Don't fail the build

if __name__ == "__main__":
    sys.exit(main())
