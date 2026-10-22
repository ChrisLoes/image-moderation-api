"""
Offensive hand gesture detection (middle finger) based on MediaPipe hand landmarks.

MediaPipe has no "middle finger" class, so the gesture is derived from the 21 hand
landmarks: the middle finger is stretched while index and ring finger are folded
(pinky mostly folded, thumb ignored). The landmark model is run on the whole image,
its mirror image and an enlarged crop around every found hand; the best score wins.
This helps because the landmark model often misreads this rare pose on a single pass.

Thresholds were calibrated on the HaGRIDv2 validation set (50 middle-finger images
vs. 1,650 images with 33 other gestures, see tests/test_gestures.py and
scripts/evaluate_detectors.py).
"""

import logging
import threading
from dataclasses import dataclass

import numpy as np

from app.model_files import ensure_model

logger = logging.getLogger(__name__)

# Landmark indices (MCP, PIP, DIP, TIP) per finger
FINGERS = {
    "index": (5, 6, 7, 8),
    "middle": (9, 10, 11, 12),
    "ring": (13, 14, 15, 16),
    "pinky": (17, 18, 19, 20),
}
WRIST = 0

_landmarker = None
_lock = threading.Lock()


@dataclass
class GestureDetection:
    label: str
    confidence: float
    box: tuple[int, int, int, int]  # x, y, w, h in pixels


def _get_landmarker():
    global _landmarker
    if _landmarker is None:
        from mediapipe.tasks.python import BaseOptions, vision

        options = vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(ensure_model("hand_landmarker"))),
            running_mode=vision.RunningMode.IMAGE,
            num_hands=6,
            min_hand_detection_confidence=0.3,
            min_hand_presence_confidence=0.3,
        )
        _landmarker = vision.HandLandmarker.create_from_options(options)
        logger.info("Hand landmarker loaded")
    return _landmarker


def _angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    v1, v2 = a - b, c - b
    cos = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-9)
    return float(np.degrees(np.arccos(np.clip(cos, -1.0, 1.0))))


def finger_extension(points: np.ndarray, finger: str) -> float:
    """0 = folded, 1 = stretched. Uses 3D world landmarks (metres, camera independent)."""
    mcp, pip, dip, tip = FINGERS[finger]
    # A stretched finger tip is ~1.3-1.45x further from the wrist than its middle joint,
    # a folded one ~0.6-0.85x.
    reach = np.linalg.norm(points[tip] - points[WRIST]) / (
        np.linalg.norm(points[pip] - points[WRIST]) + 1e-9
    )
    pip_angle = _angle(points[mcp], points[pip], points[dip])
    return float(np.clip((reach - 0.95) / 0.3, 0, 1) * np.clip((pip_angle - 115) / 40, 0, 1))


def middle_finger_score(points: np.ndarray) -> float:
    """Score in [0, 1] that a hand (21 world landmarks) shows the middle finger."""
    ext = {name: finger_extension(points, name) for name in FINGERS}
    others_folded = min(1 - ext["index"], 1 - ext["ring"])
    pinky_folded = 1 - ext["pinky"]
    return ext["middle"] * others_folded * (0.6 + 0.4 * pinky_folded)


def _detect_hands(rgb: np.ndarray):
    """Run the landmarker; returns list of (score, world_points, image_points_px)."""
    import mediapipe as mp

    h, w = rgb.shape[:2]
    image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
    with _lock:  # MediaPipe graphs are not thread safe
        result = _get_landmarker().detect(image)
    hands = []
    for world, img_pts in zip(result.hand_world_landmarks, result.hand_landmarks):
        world_points = np.array([[p.x, p.y, p.z] for p in world])
        pixel_points = np.array([[p.x * w, p.y * h] for p in img_pts])
        hands.append((middle_finger_score(world_points), pixel_points))
    return hands


def _hand_box(pixel_points: np.ndarray, w: int, h: int, margin: float) -> tuple[int, int, int, int]:
    x0, y0 = pixel_points.min(axis=0)
    x1, y1 = pixel_points.max(axis=0)
    size = max(x1 - x0, y1 - y0) * (1 + margin)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    bx0, by0 = int(max(0, cx - size / 2)), int(max(0, cy - size / 2))
    bx1, by1 = int(min(w, cx + size / 2)), int(min(h, cy + size / 2))
    return bx0, by0, bx1 - bx0, by1 - by0


def detect_offensive_gestures(rgb: np.ndarray) -> list[GestureDetection]:
    """Middle-finger score for every hand found in an RGB uint8 image (one entry per hand, score may be 0)."""
    h, w = rgb.shape[:2]
    candidates: list[tuple[float, np.ndarray]] = []

    # Pass 1: original image and mirror image (mirroring flips left/right hand handling)
    candidates += _detect_hands(rgb)
    mirrored = _detect_hands(rgb[:, ::-1])
    for score, pts in mirrored:
        pts = pts.copy()
        pts[:, 0] = w - pts[:, 0]
        candidates.append((score, pts))

    # Pass 2: enlarged crop around each hand, so the landmark model sees it in detail
    refined: list[tuple[float, np.ndarray]] = []
    for score, pts in candidates:
        x, y, bw, bh = _hand_box(pts, w, h, margin=1.0)
        if bw < 16 or bh < 16:
            continue
        crop = rgb[y : y + bh, x : x + bw]
        for crop_score, crop_pts in _detect_hands(crop):
            crop_pts = crop_pts + np.array([x, y])
            refined.append((crop_score, crop_pts))
    candidates += refined

    # Merge candidates belonging to the same hand (overlapping boxes), keep the best score
    detections: list[GestureDetection] = []
    for score, pts in sorted(candidates, key=lambda c: -c[0]):
        box = _hand_box(pts, w, h, margin=0.2)
        if any(_iou(box, d.box) > 0.3 for d in detections):
            continue
        detections.append(GestureDetection("middle_finger", round(score, 4), box))

    return detections


def _iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    ax0, ay0, aw, ah = a
    bx0, by0, bw, bh = b
    ix = max(0, min(ax0 + aw, bx0 + bw) - max(ax0, bx0))
    iy = max(0, min(ay0 + ah, by0 + bh) - max(ay0, by0))
    inter = ix * iy
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0
