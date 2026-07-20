#!/usr/bin/env python3
"""
Download the latest NSFW detection model from NudeNet releases.
This script fetches the most recent classifier_nsfw.onnx from GitHub releases.
Supports multiple download methods: urllib, curl, or wget.
"""

import os
import sys
import json
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

# Configuration
GITHUB_API_URL = "https://api.github.com/repos/notAI-tech/NudeNet/releases/latest"
MODEL_FILENAME = "classifier_nsfw.onnx"
MODELS_DIR = Path("/app/models")

def get_latest_release_url():
    """Fetch the latest release download URL from GitHub API or use direct link."""
    # Try GitHub API first
    try:
        print("Fetching latest NudeNet release info from GitHub API...")
        with urllib.request.urlopen(GITHUB_API_URL, timeout=30) as response:
            data = json.loads(response.read().decode())

            # Find the classifier_nsfw.onnx asset
            for asset in data.get("assets", []):
                if asset["name"] == MODEL_FILENAME:
                    url = asset["browser_download_url"]
                    size_mb = asset["size"] / (1024 * 1024)
                    print(f"Found: {MODEL_FILENAME} ({size_mb:.1f} MB)")
                    return url

            print(f"Asset not found in API response, using fallback direct link...")
    except (urllib.error.URLError, json.JSONDecodeError, Exception) as e:
        print(f"GitHub API unavailable: {e}")
        print("Using fallback direct download link...")

    # Fallback: Use direct GitHub release URL
    direct_url = "https://github.com/notAI-tech/NudeNet/releases/download/v3/classifier_nsfw.onnx"
    print(f"Using direct link: {direct_url}")
    return direct_url

def download_model(url):
    """Download the NSFW model from the given URL."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODELS_DIR / MODEL_FILENAME

    try:
        print(f"Downloading from: {url}")
        print(f"Saving to: {model_path}")

        # Create a request with proper headers to handle redirects
        request = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )

        # Download with progress and timeout
        def download_progress(block_num, block_size, total_size):
            if total_size > 0:
                downloaded = block_num * block_size
                percent = min(downloaded * 100 // total_size, 100)
                mb_downloaded = downloaded / (1024 * 1024)
                mb_total = total_size / (1024 * 1024)
                print(f"\rProgress: {percent}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)", end="", flush=True)

        # Set timeout to 10 minutes for large downloads
        urllib.request.urlretrieve(request, model_path, download_progress, timeout=600)
        print("\nDownload complete!")

        # Verify file
        if not model_path.exists():
            raise FileNotFoundError(f"Downloaded file not found: {model_path}")

        file_size_mb = model_path.stat().st_size / (1024 * 1024)
        if file_size_mb < 1:
            raise FileNotFoundError(f"Downloaded file is too small: {file_size_mb:.1f} MB")

        print(f"Model saved successfully: {file_size_mb:.1f} MB")
        return True
    except (urllib.error.URLError, FileNotFoundError) as e:
        print(f"Error downloading from {url}: {e}")
        return False

def download_with_curl(url, output_path):
    """Try downloading with curl as fallback."""
    try:
        print("Trying curl...")
        result = subprocess.run(
            ["curl", "-L", "-o", str(output_path), url],
            capture_output=True,
            timeout=300
        )
        return result.returncode == 0 and output_path.exists()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

def download_with_wget(url, output_path):
    """Try downloading with wget as fallback."""
    try:
        print("Trying wget...")
        result = subprocess.run(
            ["wget", "-O", str(output_path), url],
            capture_output=True,
            timeout=300
        )
        return result.returncode == 0 and output_path.exists()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

def main():
    """Main execution."""
    print("=" * 60)
    print("NSFW Model Downloader")
    print("=" * 60)

    # Check if model already exists
    model_path = MODELS_DIR / MODEL_FILENAME
    if model_path.exists():
        file_size_mb = model_path.stat().st_size / (1024 * 1024)
        print(f"Model already exists: {model_path} ({file_size_mb:.1f} MB)")
        return 0

    # Get latest release URL
    url = get_latest_release_url()
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # Try different download methods
    print("\nAttempting download...")

    # Method 1: Try urllib
    if download_model(url):
        if model_path.exists() and model_path.stat().st_size > 1000000:
            print("\nModel download successful!")
            return 0

    # Method 2: Try curl
    if download_with_curl(url, model_path):
        if model_path.exists() and model_path.stat().st_size > 1000000:
            print("Model download successful with curl!")
            return 0

    # Method 3: Try wget
    if download_with_wget(url, model_path):
        if model_path.exists() and model_path.stat().st_size > 1000000:
            print("Model download successful with wget!")
            return 0

    print("\nModel download failed with all methods!")
    print(f"Please download manually from: {url}")
    print(f"And place it at: {model_path}")
    return 1

if __name__ == "__main__":
    sys.exit(main())
