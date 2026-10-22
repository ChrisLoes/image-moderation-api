"""
Model file registry: where each model comes from, its checksum and where it lives.

Models are downloaded at Docker build time (scripts/download_models.py). If a file
is missing at runtime (e.g. local development), it is downloaded on first use.
Every file is verified against its SHA256 so a truncated or swapped download is
never loaded.
"""

import hashlib
import io
import logging
import os
import shutil
import tempfile
import threading
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

MODELS_DIR = Path(os.getenv("MODELS_DIR", "models"))


@dataclass(frozen=True)
class ModelFile:
    filename: str
    url: str
    sha256: str
    description: str
    # When the model is shipped inside a zip/wheel, the member to extract.
    archive_member: str | None = None
    archive_sha256: str | None = None


MODEL_FILES: dict[str, ModelFile] = {
    # Google MediaPipe BlazeFace (Apache 2.0) - fast, robust for close and medium faces
    "face_blazeface": ModelFile(
        filename="blaze_face_short_range.tflite",
        url="https://storage.googleapis.com/mediapipe-models/face_detector/"
        "blaze_face_short_range/float16/1/blaze_face_short_range.tflite",
        sha256="b4578f35940bf5a1a655214a1cce5cab13eba73c1297cd78e1a04c2380b0152f",
        description="MediaPipe BlazeFace short-range face detector",
    ),
    # OpenCV YuNet (MIT) - multi-scale detector, finds small, tilted and partly hidden faces
    "face_yunet": ModelFile(
        filename="face_detection_yunet_2023mar.onnx",
        url="https://huggingface.co/opencv/face_detection_yunet/resolve/main/"
        "face_detection_yunet_2023mar.onnx",
        sha256="8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
        description="OpenCV YuNet face detector",
    ),
    # Google MediaPipe hand landmarks (Apache 2.0) - used for offensive gesture detection
    "hand_landmarker": ModelFile(
        filename="hand_landmarker.task",
        url="https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
        "hand_landmarker/float16/1/hand_landmarker.task",
        sha256="fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1",
        description="MediaPipe hand landmarker",
    ),
    # NudeNet v3 detector (YOLOv8n, 18 body-part classes), shipped inside the PyPI wheel
    "nudenet": ModelFile(
        filename="nudenet_320n.onnx",
        url="https://files.pythonhosted.org/packages/1c/ee/"
        "1aa02d44ba958cc77e16ff1e41a0aac5e721037db7bf62b9c9d124917f87/"
        "nudenet-3.4.2-py3-none-any.whl",
        sha256="c15d8273adad2d0a92f014cc69ab2d6c311a06777a55545f2c4eb46f51911f0f",
        description="NudeNet v3 body-part detector (320n)",
        archive_member="nudenet/320n.onnx",
        archive_sha256="5937dbd84e5d8e5de038f08ffea5a1bb50a08475776bf2b4795914ce0eaf0331",
    ),
}

_download_lock = threading.Lock()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def model_path(key: str) -> Path:
    return MODELS_DIR / MODEL_FILES[key].filename


def is_available(key: str) -> bool:
    return model_path(key).is_file()


def _download(url: str, timeout: int = 300) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "image-moderation-api"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def download_model(key: str) -> Path:
    """Download (and verify) a model file. Raises RuntimeError on failure."""
    spec = MODEL_FILES[key]
    target = model_path(key)
    target.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Downloading model '{key}' from {spec.url}")
    data = _download(spec.url)

    if spec.archive_member:
        if spec.archive_sha256 and _sha256(data) != spec.archive_sha256:
            raise RuntimeError(f"Checksum mismatch for archive of model '{key}'")
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            data = archive.read(spec.archive_member)

    if _sha256(data) != spec.sha256:
        raise RuntimeError(f"Checksum mismatch for model '{key}'")

    # Write atomically so a half-written file is never picked up
    fd, tmp_name = tempfile.mkstemp(dir=target.parent, prefix=f".{spec.filename}.")
    with os.fdopen(fd, "wb") as tmp:
        tmp.write(data)
    shutil.move(tmp_name, target)
    logger.info(f"Model '{key}' saved to {target} ({len(data) / 1024 / 1024:.1f} MB)")
    return target


def ensure_model(key: str) -> Path:
    """Return the path of a model, downloading it first if it is missing or corrupt."""
    target = model_path(key)
    with _download_lock:
        if target.is_file():
            if _file_sha256(target) == MODEL_FILES[key].sha256:
                return target
            logger.warning(f"Model '{key}' at {target} has a wrong checksum, downloading again")
        return download_model(key)
