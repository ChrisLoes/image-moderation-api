"""
Face detection ensemble.

Two detectors with different strengths are combined and their boxes merged:

- OpenCV YuNet: multi-scale CNN, finds small, tilted and partly hidden faces
  (crowds, group photos, people further away).
- MediaPipe BlazeFace (Tasks API): very reliable for close and large faces (selfies).
  Its input is only 128x128 px, so on its own it misses small faces. (Running it on image
  tiles was tested: +0.5 % faces found, but 0.3 more false boxes per image.)

Overlapping boxes from both detectors are merged (non-maximum suppression), so every
face is counted and blurred once. Detection quality is measured with
scripts/evaluate_detectors.py on the WIDER FACE validation set.
"""

import logging
import threading
from dataclasses import dataclass

import cv2
import numpy as np

from app.model_files import ensure_model

logger = logging.getLogger(__name__)

# YuNet works on the image itself; very large images are scaled down for speed.
# 2048 px keeps faces of ~10 px (WIDER "hard") detectable.
YUNET_MAX_SIDE = 2048

_blazeface = None
_yunet = None
_blazeface_lock = threading.Lock()
_yunet_lock = threading.Lock()


@dataclass
class FaceBox:
    x: int
    y: int
    w: int
    h: int
    score: float
    source: str


def _get_blazeface():
    global _blazeface
    if _blazeface is None:
        from mediapipe.tasks.python import BaseOptions, vision

        options = vision.FaceDetectorOptions(
            base_options=BaseOptions(model_asset_path=str(ensure_model("face_blazeface"))),
            running_mode=vision.RunningMode.IMAGE,
            # Filtering by the requested confidence happens below, so all candidates are kept
            min_detection_confidence=0.2,
            min_suppression_threshold=0.3,
        )
        _blazeface = vision.FaceDetector.create_from_options(options)
        logger.info("MediaPipe BlazeFace face detector loaded")
    return _blazeface


def _get_yunet():
    global _yunet
    if _yunet is None:
        _yunet = cv2.FaceDetectorYN.create(
            str(ensure_model("face_yunet")),
            "",
            (320, 320),
            score_threshold=0.3,
            nms_threshold=0.3,
            top_k=5000,
        )
        logger.info("OpenCV YuNet face detector loaded")
    return _yunet


def _blazeface_detect(rgb: np.ndarray) -> list[FaceBox]:
    import mediapipe as mp

    image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
    with _blazeface_lock:  # MediaPipe graphs are not thread safe
        result = _get_blazeface().detect(image)
    boxes = []
    for detection in result.detections:
        bb = detection.bounding_box
        score = detection.categories[0].score if detection.categories else 0.0
        boxes.append(FaceBox(bb.origin_x, bb.origin_y, bb.width, bb.height, score, "blazeface"))
    return boxes


def _yunet_detect(rgb: np.ndarray) -> list[FaceBox]:
    h, w = rgb.shape[:2]
    scale = min(1.0, YUNET_MAX_SIDE / max(w, h))
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    if scale < 1.0:
        bgr = cv2.resize(bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    with _yunet_lock:
        detector = _get_yunet()
        detector.setInputSize((bgr.shape[1], bgr.shape[0]))
        _, faces = detector.detect(bgr)
    boxes = []
    if faces is not None:
        for face in faces:
            x, y, fw, fh = (face[:4] / scale).tolist()
            boxes.append(FaceBox(int(x), int(y), int(fw), int(fh), float(face[14]), "yunet"))
    return boxes


def _overlap(a: FaceBox, b: FaceBox) -> tuple[float, float]:
    """IoU and share of the smaller box covered by the other."""
    ix = max(0, min(a.x + a.w, b.x + b.w) - max(a.x, b.x))
    iy = max(0, min(a.y + a.h, b.y + b.h) - max(a.y, b.y))
    inter = ix * iy
    area_a, area_b = a.w * a.h, b.w * b.h
    union = area_a + area_b - inter
    iou = inter / union if union > 0 else 0.0
    smaller = min(area_a, area_b)
    return iou, (inter / smaller if smaller > 0 else 0.0)


def merge_boxes(boxes: list[FaceBox]) -> list[FaceBox]:
    """Non-maximum suppression; also drops boxes that lie mostly inside a kept one."""
    kept: list[FaceBox] = []
    for box in sorted(boxes, key=lambda b: -b.score):
        if box.w <= 0 or box.h <= 0:
            continue
        if any(iou > 0.3 or contained > 0.7 for iou, contained in (_overlap(box, k) for k in kept)):
            continue
        kept.append(box)
    return kept


def detect_faces(rgb: np.ndarray, confidence: float) -> list[FaceBox]:
    """
    Detect faces in an RGB uint8 image.

    `confidence` is the minimum score (0-1) a face needs. Both detectors report scores
    on a comparable scale; YuNet is slightly stricter, so its scores are used as is.
    """
    h, w = rgb.shape[:2]
    candidates: list[FaceBox] = []
    failures = 0

    try:
        candidates += _yunet_detect(rgb)
    except Exception as e:  # keep working with the other detector
        failures += 1
        logger.error(f"YuNet face detection failed: {e}", exc_info=True)

    try:
        candidates += _blazeface_detect(rgb)
    except Exception as e:
        failures += 1
        logger.error(f"BlazeFace face detection failed: {e}", exc_info=True)

    if failures == 2:
        # Never report "0 faces" when nothing could be checked - the caller would publish
        # the image unblurred.
        raise RuntimeError("No face detector available")

    faces = merge_boxes([b for b in candidates if b.score >= confidence])

    # Clip to the image
    clipped = []
    for f in faces:
        x0, y0 = max(0, f.x), max(0, f.y)
        x1, y1 = min(w, f.x + f.w), min(h, f.y + f.h)
        if x1 > x0 and y1 > y0:
            clipped.append(FaceBox(x0, y0, x1 - x0, y1 - y0, f.score, f.source))

    logger.debug(
        f"Face detection - candidates: {len(candidates)}, faces: {len(clipped)}, "
        f"confidence: {confidence}"
    )
    return clipped
