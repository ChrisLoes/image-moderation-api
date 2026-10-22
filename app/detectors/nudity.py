"""
Nudity detection with the NudeNet v3 body-part detector (YOLOv8n, ONNX).

NudeNet finds body parts (e.g. FEMALE_BREAST_EXPOSED) with a box and a score. They are
grouped into two categories:

- nude: exposed genitals, anus, female breasts or buttocks
- partially_nude: the same parts covered (underwear, swimwear, tight clothing)

The model runs at 320 px (its training size) and at 640 px, so small regions in large
photos are found as well; per class the best score counts.
"""

import logging
import threading
from dataclasses import dataclass

import cv2
import numpy as np

from app.model_files import ensure_model

logger = logging.getLogger(__name__)

LABELS = [
    "FEMALE_GENITALIA_COVERED",
    "FACE_FEMALE",
    "BUTTOCKS_EXPOSED",
    "FEMALE_BREAST_EXPOSED",
    "FEMALE_GENITALIA_EXPOSED",
    "MALE_BREAST_EXPOSED",
    "ANUS_EXPOSED",
    "FEET_EXPOSED",
    "BELLY_COVERED",
    "FEET_COVERED",
    "ARMPITS_COVERED",
    "ARMPITS_EXPOSED",
    "FACE_MALE",
    "BELLY_EXPOSED",
    "MALE_GENITALIA_EXPOSED",
    "ANUS_COVERED",
    "FEMALE_BREAST_COVERED",
    "BUTTOCKS_COVERED",
]

NUDE_CLASSES = {
    "FEMALE_GENITALIA_EXPOSED",
    "MALE_GENITALIA_EXPOSED",
    "ANUS_EXPOSED",
    "FEMALE_BREAST_EXPOSED",
    "BUTTOCKS_EXPOSED",
}
PARTIAL_CLASSES = {
    "FEMALE_GENITALIA_COVERED",
    "ANUS_COVERED",
    "FEMALE_BREAST_COVERED",
    "BUTTOCKS_COVERED",
}

INFERENCE_SIZES = (320, 640)
MIN_SCORE = 0.2

_session = None
_lock = threading.Lock()


@dataclass
class BodyPart:
    label: str
    score: float
    box: tuple[int, int, int, int]  # x, y, w, h in pixels


def _get_session():
    global _session
    if _session is None:
        import onnxruntime as ort

        _session = ort.InferenceSession(
            str(ensure_model("nudenet")), providers=["CPUExecutionProvider"]
        )
        logger.info("NudeNet detector loaded")
    return _session


def _detect_at(rgb: np.ndarray, size: int) -> list[BodyPart]:
    h, w = rgb.shape[:2]
    side = max(h, w)
    # Letterbox to a centred square with grey borders, like the YOLOv8 training pipeline.
    # (Black bottom/right padding, as in the NudeNet package, causes false hits at the edge.)
    pad_x, pad_y = (side - w) // 2, (side - h) // 2
    padded = cv2.copyMakeBorder(
        rgb, pad_y, side - h - pad_y, pad_x, side - w - pad_x, cv2.BORDER_CONSTANT, value=(114, 114, 114)
    )
    blob = cv2.dnn.blobFromImage(padded, 1 / 255.0, (size, size), (0, 0, 0), swapRB=False, crop=False)

    session = _get_session()
    with _lock:
        output = session.run(None, {session.get_inputs()[0].name: blob})[0]

    rows = np.transpose(np.squeeze(output, axis=0))  # (n, 4 + classes)
    scores = rows[:, 4:]
    class_ids = np.argmax(scores, axis=1)
    best = scores[np.arange(len(rows)), class_ids]
    keep = best >= MIN_SCORE
    rows, class_ids, best = rows[keep], class_ids[keep], best[keep]

    scale = side / size
    boxes = []
    for (cx, cy, bw, bh), _ in zip(rows[:, :4], best):
        x = max(0.0, (cx - bw / 2) * scale - pad_x)
        y = max(0.0, (cy - bh / 2) * scale - pad_y)
        boxes.append([x, y, min(bw * scale, w - x), min(bh * scale, h - y)])

    indices = cv2.dnn.NMSBoxes(boxes, best.tolist(), MIN_SCORE, 0.45) if boxes else []
    return [
        BodyPart(
            LABELS[int(class_ids[i])],
            float(best[i]),
            tuple(int(v) for v in boxes[i]),
        )
        for i in np.array(indices).flatten()
    ]


def detect_body_parts(rgb: np.ndarray) -> list[BodyPart]:
    """All body parts found in an RGB uint8 image (both inference sizes combined)."""
    parts: list[BodyPart] = []
    for size in INFERENCE_SIZES:
        parts += _detect_at(rgb, size)
    return parts


def nudity_scores(parts: list[BodyPart]) -> dict[str, float]:
    """Highest score per category: {'nude': .., 'partially_nude': ..}."""
    nude = max((p.score for p in parts if p.label in NUDE_CLASSES), default=0.0)
    partial = max((p.score for p in parts if p.label in PARTIAL_CLASSES), default=0.0)
    return {"nude": round(nude, 4), "partially_nude": round(partial, 4)}
