#!/usr/bin/env python3
"""
Download and verify all detection models (faces, nudity, hand gestures).

Used at Docker build time; exits with 1 if a model cannot be downloaded, so an image
without models is never built. Run locally with: MODELS_DIR=models python scripts/download_models.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.model_files import MODEL_FILES, ensure_model  # noqa: E402


def main() -> int:
    failed = []
    for key, spec in MODEL_FILES.items():
        try:
            path = ensure_model(key)
            print(f"OK   {key:16s} {path} ({path.stat().st_size / 1024 / 1024:.1f} MB) - {spec.description}")
        except Exception as e:
            print(f"FAIL {key:16s} {spec.url}: {e}")
            failed.append(key)
    if failed:
        print(f"Model download failed: {', '.join(failed)}")
        return 1
    print("All models ready")
    return 0


if __name__ == "__main__":
    sys.exit(main())
