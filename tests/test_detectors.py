"""
Unit tests for the detection logic (faces, nudity, gestures) and request handling.

Models are downloaded on first use (MODELS_DIR, default ./models). The recognition
quality on real photos is measured with scripts/evaluate_detectors.py.
"""

import io
import sys
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings  # noqa: E402
from app.detectors import faces, gestures, nudity  # noqa: E402
from app.main import app  # noqa: E402
from app.routers.nsfw import nsfw_score_from  # noqa: E402

client = TestClient(app)
HEADERS = {"X-API-Key": "test-key"}


# --- Hand skeletons (21 world landmarks in metres) -------------------------------

FINGER_X = {"index": -0.03, "middle": -0.01, "ring": 0.01, "pinky": 0.03}


def make_hand(stretched: set[str]) -> np.ndarray:
    """Hand pointing up; fingers in `stretched` are straight, the others folded into the palm."""
    points = np.zeros((21, 3))
    points[1:5] = [[-0.04, 0.03, 0], [-0.05, 0.05, 0.01], [-0.04, 0.06, 0.03], [-0.03, 0.06, 0.04]]  # thumb tucked
    for name, (mcp, pip, dip, tip) in gestures.FINGERS.items():
        x = FINGER_X[name]
        points[mcp] = [x, 0.08, 0]
        if name in stretched:
            points[pip] = [x, 0.12, 0]
            points[dip] = [x, 0.15, 0]
            points[tip] = [x, 0.175, 0]
        else:
            points[pip] = [x, 0.11, 0.02]
            points[dip] = [x, 0.09, 0.04]
            points[tip] = [x, 0.07, 0.03]
    return points


class TestMiddleFingerRule:
    """Gesture -> score. Stretched fingers per gesture; thumb is ignored."""

    @pytest.mark.parametrize(
        "gesture, stretched, expected_flag",
        [
            ("middle finger", {"middle"}, True),
            ("middle finger, pinky half open", {"middle", "pinky"}, True),
            ("fist", set(), False),
            ("open hand", {"index", "middle", "ring", "pinky"}, False),
            ("pointing (index)", {"index"}, False),
            ("peace / victory", {"index", "middle"}, False),
            ("three fingers", {"index", "middle", "ring"}, False),
            ("pinky", {"pinky"}, False),
            ("rock", {"index", "pinky"}, False),
        ],
    )
    def test_gestures(self, gesture, stretched, expected_flag):
        score = gestures.middle_finger_score(make_hand(stretched))
        assert (score > 0.5) is expected_flag, f"{gesture}: score {score:.2f}"

    def test_score_is_rotation_invariant(self):
        hand = make_hand({"middle"})
        angle = np.radians(120)
        rotation = np.array(
            [[np.cos(angle), -np.sin(angle), 0], [np.sin(angle), np.cos(angle), 0], [0, 0, 1]]
        )
        assert gestures.middle_finger_score(hand @ rotation.T) == pytest.approx(
            gestures.middle_finger_score(hand)
        )


class TestFaceBoxMerge:
    def test_overlapping_boxes_from_both_detectors_count_once(self):
        boxes = [
            faces.FaceBox(100, 100, 50, 60, 0.9, "yunet"),
            faces.FaceBox(104, 98, 48, 58, 0.8, "blazeface"),
        ]
        merged = faces.merge_boxes(boxes)
        assert len(merged) == 1
        assert merged[0].source == "yunet"

    def test_box_inside_bigger_box_is_dropped(self):
        boxes = [
            faces.FaceBox(100, 100, 100, 100, 0.9, "yunet"),
            faces.FaceBox(130, 130, 30, 30, 0.6, "blazeface"),
        ]
        assert len(faces.merge_boxes(boxes)) == 1

    def test_separate_faces_are_kept(self):
        boxes = [
            faces.FaceBox(0, 0, 40, 40, 0.9, "yunet"),
            faces.FaceBox(200, 0, 40, 40, 0.7, "blazeface"),
        ]
        assert len(faces.merge_boxes(boxes)) == 2


class TestNsfwScore:
    """nsfw_score = max(nude, offensive_gesture, partially_nude * 0.5)"""

    @pytest.mark.parametrize(
        "nude, partial, gesture, expected",
        [
            (0.0, 0.0, 0.0, 0.0),
            (0.9, 0.0, 0.0, 0.9),
            (0.0, 0.9, 0.0, 0.45),  # swimwear alone never exceeds 0.5
            (0.0, 0.0, 0.8, 0.8),  # middle finger
            (0.3, 0.8, 0.7, 0.7),
        ],
    )
    def test_combination(self, nude, partial, gesture, expected):
        scores = {"nude": nude, "partially_nude": partial, "offensive_gesture": gesture}
        assert nsfw_score_from(scores) == pytest.approx(expected)

    def test_categories(self):
        parts = [
            nudity.BodyPart("FEMALE_BREAST_COVERED", 0.7, (0, 0, 10, 10)),
            nudity.BodyPart("BUTTOCKS_EXPOSED", 0.6, (0, 0, 10, 10)),
            nudity.BodyPart("FACE_FEMALE", 0.95, (0, 0, 10, 10)),
        ]
        assert nudity.nudity_scores(parts) == {"nude": 0.6, "partially_nude": 0.7}


class TestIntensity:
    def test_higher_face_intensity_finds_more_faces(self):
        assert (
            settings.get_face_detection_confidence("high")
            < settings.get_face_detection_confidence("medium")
            < settings.get_face_detection_confidence("low")
        )


# --- Real models on synthetic images ----------------------------------------------


def png_bytes(image: Image.Image, **save_args) -> io.BytesIO:
    buffer = io.BytesIO()
    image.save(buffer, **save_args)
    buffer.seek(0)
    return buffer


def plain_image(width=640, height=480) -> Image.Image:
    rng = np.random.default_rng(0)
    gradient = np.linspace(60, 200, width, dtype=np.uint8)[None, :, None]
    noise = rng.integers(0, 20, (height, width, 3), dtype=np.uint8)
    return Image.fromarray(np.clip(gradient + noise, 0, 255).astype(np.uint8))


FIXTURES = Path(__file__).parent / "fixtures"


def face_photo() -> Image.Image:
    return Image.open(FIXTURES / "astronaut.jpg").convert("RGB")


class TestFacesOnRealPhoto:
    """NASA portrait (public domain): one face, at different sizes."""

    def test_portrait(self):
        assert len(faces.detect_faces(np.array(face_photo()), 0.5)) == 1

    def test_close_up_selfie(self):
        """Face fills most of a large photo (~1300 px)."""
        big = face_photo().resize((3000, 3000))
        assert len(faces.detect_faces(np.array(big.crop((600, 0, 2400, 1800))), 0.5)) == 1

    def test_small_faces_in_group(self):
        canvas = Image.new("RGB", (1600, 900), (90, 110, 130))
        x = 20
        for size in (420, 300, 220, 160, 120, 90):  # face height down to ~40 px
            canvas.paste(face_photo().resize((size, size)), (x, 450 - size // 2))
            x += size + 20
        assert len(faces.detect_faces(np.array(canvas), 0.5)) == 6

    def test_sideways_phone_photo_via_exif(self):
        """Stored sideways with EXIF flag -> turned upright before detection."""
        rotated = face_photo().rotate(90, expand=True)
        exif = Image.Exif()
        exif[0x0112] = 6
        response = client.post(
            "/faces/blur",
            files={"file": ("p.jpg", png_bytes(rotated, format="JPEG", exif=exif), "image/jpeg")},
            headers=HEADERS,
        )
        assert response.status_code == 200
        assert response.json()["faces_detected"] == 1


class TestModelsOnPlainImage:
    """Loads every model and runs it on an image without people."""

    def test_no_faces(self):
        assert faces.detect_faces(np.array(plain_image()), 0.5) == []

    def test_no_nudity(self):
        scores = nudity.nudity_scores(nudity.detect_body_parts(np.array(plain_image())))
        assert scores["nude"] < 0.3

    def test_no_gesture(self):
        hands = gestures.detect_offensive_gestures(np.array(plain_image()))
        assert all(h.confidence < 0.5 for h in hands)

    def test_nsfw_endpoint_reports_safe(self):
        response = client.post(
            "/nsfw/check",
            files={"file": ("plain.png", png_bytes(plain_image(), format="PNG"), "image/png")},
            params={"return_details": "true"},
            headers=HEADERS,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_nsfw"] is False
        assert data["primary_detection"] == "safe"
        assert data["reasons"] == []
        assert set(data["detections"]) == {"safe", "nude", "partially_nude", "offensive_gesture"}

    def test_nsfw_options_as_form_fields(self):
        """wievoll-next sends options as multipart fields next to the file."""
        response = client.post(
            "/nsfw/check",
            files={"file": ("plain.png", png_bytes(plain_image(), format="PNG"), "image/png")},
            data={"return_details": "true", "intensity": "high"},
            headers=HEADERS,
        )
        assert response.status_code == 200
        assert response.json()["detections"] is not None

    def test_face_blur_endpoint(self):
        response = client.post(
            "/faces/blur",
            files={"file": ("plain.png", png_bytes(plain_image(), format="PNG"), "image/png")},
            headers=HEADERS,
        )
        assert response.status_code == 200
        assert response.json()["faces_detected"] == 0


def test_exif_orientation_is_applied():
    """Phone photos stored sideways with an EXIF rotation flag are turned upright."""
    image = plain_image(400, 200)
    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90° clockwise when displaying
    response = client.post(
        "/faces/blur",
        files={"file": ("photo.jpg", png_bytes(image, format="JPEG", exif=exif), "image/jpeg")},
        headers=HEADERS,
    )
    assert response.status_code == 200
    import base64

    result = Image.open(io.BytesIO(base64.b64decode(response.json()["processed_image_base64"])))
    assert result.size == (200, 400)
