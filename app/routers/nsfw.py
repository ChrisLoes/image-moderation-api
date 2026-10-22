import logging
from typing import Optional

import numpy as np
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.concurrency import run_in_threadpool

from app.auth import verify_api_key
from app.config import settings
from app.detectors import gestures, nudity
from app.models import NSFWCheckResponse, NSFWDetection
from app.utils import form_fallback, parse_bool, parse_number, validate_image

router = APIRouter(prefix="/nsfw", tags=["NSFW Detection"])
logger = logging.getLogger(__name__)

# Swimwear/underwear ("partially_nude") alone should never outweigh real nudity:
# it counts half towards nsfw_score, so it stays <= 0.5.
PARTIAL_WEIGHT = 0.5
# Genital/buttock hits that lie mostly inside a hand are almost always fingers
HAND_OVERLAP_CLASSES = {"MALE_GENITALIA_EXPOSED", "FEMALE_GENITALIA_EXPOSED", "BUTTOCKS_EXPOSED", "ANUS_EXPOSED"}


def _covered_by(inner: tuple[int, int, int, int], outer: tuple[int, int, int, int]) -> float:
    ix0, iy0, iw, ih = inner
    ox0, oy0, ow, oh = outer
    w = max(0, min(ix0 + iw, ox0 + ow) - max(ix0, ox0))
    h = max(0, min(iy0 + ih, oy0 + oh) - max(iy0, oy0))
    return (w * h) / (iw * ih) if iw * ih > 0 else 0.0


def analyze_image(rgb: np.ndarray, check_gestures: bool) -> tuple[dict[str, float], list[NSFWDetection]]:
    """Run all NSFW detectors. Returns category scores and individual findings."""
    hands = gestures.detect_offensive_gestures(rgb) if check_gestures else []
    parts = nudity.detect_body_parts(rgb)

    parts = [
        p
        for p in parts
        if not (p.label in HAND_OVERLAP_CLASSES and any(_covered_by(p.box, h.box) > 0.5 for h in hands))
    ]

    findings: list[NSFWDetection] = []
    for p in parts:
        if p.label in nudity.NUDE_CLASSES:
            category = "nude"
        elif p.label in nudity.PARTIAL_CLASSES:
            category = "partially_nude"
        else:
            continue
        findings.append(NSFWDetection(label=p.label, category=category, confidence=round(p.score, 4), box=list(p.box)))
    for h in hands:
        if h.confidence > 0:
            findings.append(
                NSFWDetection(label=h.label, category="offensive_gesture", confidence=h.confidence, box=list(h.box))
            )

    scores = nudity.nudity_scores(parts)
    scores["offensive_gesture"] = max((h.confidence for h in hands), default=0.0)
    return scores, sorted(findings, key=lambda f: -f.confidence)


def nsfw_score_from(scores: dict[str, float]) -> float:
    return round(
        max(scores["nude"], scores["offensive_gesture"], scores["partially_nude"] * PARTIAL_WEIGHT), 4
    )


@router.post(
    "/check",
    response_model=NSFWCheckResponse,
    summary="Check image for NSFW content",
    description="Analyze an image for nudity (NudeNet v3 body-part detector) and offensive hand "
    "gestures (middle finger, MediaPipe hand landmarks). Returns an overall nsfw_score, a boolean "
    "flag and the reasons.",
    responses={
        200: {
            "description": "Successfully analyzed image",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "is_nsfw": True,
                        "nsfw_score": 0.91,
                        "confidence": 0.91,
                        "primary_detection": "offensive_gesture",
                        "reasons": ["offensive_gesture"],
                        "detections": {
                            "safe": 0.09,
                            "partially_nude": 0.0,
                            "nude": 0.0,
                            "offensive_gesture": 0.91,
                        },
                    }
                }
            },
        },
        400: {"description": "Invalid image format or dimensions"},
        401: {"description": "Missing or invalid API key"},
        413: {"description": "File too large (exceeds MAX_FILE_SIZE)"},
        503: {"description": "NSFW model could not be loaded"},
    },
)
async def check_nsfw(
    request: Request,
    file: UploadFile = File(
        ...,
        description="Image file to analyze (JPEG, PNG, GIF, WebP, HEIC). Max 8 MB, max 4000×4000 px.",
    ),
    intensity: Optional[str] = None,
    threshold: Optional[float] = None,
    return_details: Optional[bool] = None,
    check_gestures: Optional[bool] = None,
    api_key: str = Depends(verify_api_key),
) -> NSFWCheckResponse:
    """
    Detect NSFW content in an image.

    ## How It Works
    1. **Nudity**: NudeNet v3 finds body parts (exposed or covered) at two resolutions
    2. **Offensive gestures**: MediaPipe hand landmarks; a stretched middle finger with
       folded index and ring finger counts as "middle finger"
    3. Scores are combined into `nsfw_score` and compared against the threshold

    ## Categories
    - **safe**: nothing found
    - **partially_nude**: covered intimate areas (underwear, swimwear) – counts half
    - **nude**: exposed genitals, anus, female breasts or buttocks
    - **offensive_gesture**: middle finger

    ## Parameter Priority (highest to lowest)
    1. Explicit `threshold` parameter
    2. `intensity` level (low/medium/high)
    3. Environment/config defaults

    ## Intensity Levels
    - **low**: Threshold=0.8 (lenient, only flag obvious NSFW)
    - **medium**: Threshold=0.6 (balanced) - Recommended default
    - **high**: Threshold=0.4 (strict, flags questionable content)

    ## Other Parameters
    - `return_details=true`: scores for all categories and the individual findings with boxes
    - `check_gestures=false`: skip gesture detection (default from `NSFW_CHECK_GESTURES`, true)

    All options can be sent as query parameters or as multipart form fields next to the file.
    """
    params = await form_fallback(
        request,
        {
            "intensity": intensity,
            "threshold": threshold,
            "return_details": return_details,
            "check_gestures": check_gestures,
        },
    )
    intensity = params["intensity"]
    threshold = parse_number(params["threshold"], float, "threshold")
    return_details = parse_bool(params["return_details"])
    check_gestures = parse_bool(params["check_gestures"])
    logger.debug(
        f"NSFW check request - intensity: {intensity}, threshold: {threshold}, "
        f"return_details: {return_details}, check_gestures: {check_gestures}"
    )

    pil_image = await validate_image(file)
    rgb = np.array(pil_image)
    gestures_enabled = settings.nsfw_check_gestures if check_gestures is None else check_gestures

    if threshold is not None:
        decision_threshold = threshold
    elif intensity:
        decision_threshold = settings.get_nsfw_threshold(intensity)
    else:
        decision_threshold = settings.nsfw_threshold

    try:
        scores, findings = await run_in_threadpool(analyze_image, rgb, gestures_enabled)
    except (RuntimeError, OSError) as e:
        # Model missing and download failed
        logger.error(f"NSFW model unavailable: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NSFW detection model not available",
        )
    except Exception as e:
        logger.error(f"Error during NSFW detection: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing image",
        )

    nsfw_score = nsfw_score_from(scores)
    is_nsfw = nsfw_score > decision_threshold

    weighted = {
        "nude": scores["nude"],
        "offensive_gesture": scores["offensive_gesture"],
        "partially_nude": scores["partially_nude"] * PARTIAL_WEIGHT,
    }
    reasons = [category for category, score in weighted.items() if score > decision_threshold]
    if is_nsfw:
        primary_detection = max(weighted, key=weighted.get)
        confidence = scores[primary_detection]
    else:
        primary_detection = "safe"
        confidence = round(1 - nsfw_score, 4)

    response = NSFWCheckResponse(
        success=True,
        is_nsfw=is_nsfw,
        nsfw_score=nsfw_score,
        confidence=confidence,
        primary_detection=primary_detection,
        reasons=reasons,
        detections={"safe": round(1 - nsfw_score, 4), **scores} if return_details else None,
        findings=findings if return_details else None,
    )

    log_level = logging.WARNING if is_nsfw else logging.INFO
    logger.log(
        log_level,
        f"NSFW check completed - is_nsfw: {is_nsfw}, nsfw_score: {nsfw_score:.3f}, "
        f"primary: {primary_detection}, reasons: {reasons}, threshold: {decision_threshold}, "
        f"scores: {scores}",
    )
    return response
