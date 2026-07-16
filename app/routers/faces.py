import cv2
import numpy as np
import mediapipe as mp
import logging
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from typing import Optional
from app.auth import verify_api_key
from app.models import BlurFacesRequest, BlurFacesResponse
from app.utils import validate_image, image_to_base64
from app.config import settings

router = APIRouter(prefix="/faces", tags=["Face Detection"])
logger = logging.getLogger(__name__)

mp_face_detection = mp.solutions.face_detection


def get_face_detector(confidence: float | None = None):
    """Get face detector with specified confidence threshold."""
    threshold = confidence or settings.face_detection_confidence
    return mp_face_detection.FaceDetection(
        static_image_mode=True,  # Essential for static images - enables face tracking across frames
        model_selection=0,  # 0=short-range (efficient, <2m), 1=full-range (slower, up to 5m)
        min_detection_confidence=threshold
    )


def apply_gaussian_blur(face_region: np.ndarray, blur_k: int) -> np.ndarray:
    """Apply Gaussian blur to face region."""
    return cv2.GaussianBlur(face_region, (blur_k, blur_k), 0)


def apply_pixelation(face_region: np.ndarray, pixel_size: int) -> np.ndarray:
    """Apply pixelation/pixelate blur to face region."""
    # Ensure pixel_size is at least 1
    pixel_size = max(1, pixel_size)

    # Resize down to reduce resolution
    h, w = face_region.shape[:2]
    small_h = max(1, h // pixel_size)
    small_w = max(1, w // pixel_size)

    # Resize down then up to create pixelation effect
    small = cv2.resize(face_region, (small_w, small_h), interpolation=cv2.INTER_LINEAR)
    pixelated = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)

    return pixelated


def apply_hybrid_blur(face_region: np.ndarray, blur_k: int, pixel_size: int = 5) -> np.ndarray:
    """Apply hybrid blur: combination of pixelation and Gaussian blur."""
    # First pixelate
    pixelated = apply_pixelation(face_region, pixel_size)
    # Then apply light Gaussian blur
    hybrid = cv2.GaussianBlur(pixelated, (blur_k // 2, blur_k // 2), 0) if blur_k > 2 else pixelated
    return hybrid


@router.post(
    "/blur",
    response_model=BlurFacesResponse,
    summary="Detect and blur faces in image",
    description="Detect all faces in an image using MediaPipe and apply configurable blur effect. "
    "Supports three intensity levels for automatic configuration or manual parameter tuning.",
    responses={
        200: {
            "description": "Successfully processed image",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Successfully processed image and blurred 2 face(s)",
                        "faces_detected": 2,
                        "processed_image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
                    }
                }
            },
        },
        400: {"description": "Invalid image format or dimensions"},
        401: {"description": "Missing or invalid API key"},
        413: {"description": "File too large (exceeds MAX_FILE_SIZE)"},
    },
)
async def blur_faces(
    file: UploadFile = File(
        ...,
        description="Image file to process (JPEG, PNG, GIF, WebP). Max 8 MB, max 4000×4000 px.",
    ),
    intensity: Optional[str] = None,
    blur_strength: Optional[int] = None,
    confidence_threshold: Optional[float] = None,
    face_padding: Optional[int] = None,
    blur_method: Optional[str] = None,
    api_key: str = Depends(verify_api_key),
) -> BlurFacesResponse:
    """
    Detect faces in image and apply blur effect.

    ## How It Works
    1. Receives image file and configuration parameters
    2. Uses MediaPipe face detection to locate faces
    3. Applies blur to detected face regions (Gaussian, Pixelate, or Hybrid)
    4. Returns blurred image as base64-encoded PNG

    ## Parameter Priority (highest to lowest)
    1. Explicit parameters (`blur_strength`, `confidence_threshold`, `face_padding`, `blur_method`)
    2. `intensity` level (low/medium/high)
    3. Environment/config defaults

    ## Intensity Levels
    - **low**: Confidence=0.3, Blur=11px (minimal, only obvious faces)
    - **medium**: Confidence=0.5, Blur=25px (balanced, recommended)
    - **high**: Confidence=0.8, Blur=41px (aggressive, all possible faces)

    ## Blur Methods
    - **gaussian**: Smooth Gaussian blur (default, natural looking)
    - **pixelate**: Pixelated/verpixelt effect (strong privacy, blocky)
    - **hybrid**: Combination of pixelation + light Gaussian blur (balanced)

    ## Examples
    - Basic: `POST /faces/blur -F "file=@image.jpg"`
    - High intensity: `POST /faces/blur -F "file=@image.jpg" -F "intensity=high"`
    - Strong pixelation: `POST /faces/blur -F "file=@image.jpg" -F "blur_strength=150" -F "blur_method=pixelate"`
    - Custom blur: `POST /faces/blur -F "file=@image.jpg" -F "blur_strength=35" -F "blur_method=gaussian"`
    - With padding: `POST /faces/blur -F "file=@image.jpg" -F "blur_strength=25" -F "face_padding=20"`
    """
    logger.debug(f"Face blur request - intensity: {intensity}, blur_strength: {blur_strength}, face_padding: {face_padding}, blur_method: {blur_method}")

    # Validate image
    pil_image = await validate_image(file)
    logger.debug(f"Image validated - size: {pil_image.size}")

    # Convert PIL Image to OpenCV format
    cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    h, w = cv_image.shape[:2]

    # Get blur parameters - priority: direct param > intensity > config
    if blur_strength is not None:
        blur_k = blur_strength
    elif intensity:
        blur_k = settings.get_blur_strength(intensity)
    else:
        blur_k = settings.face_blur_strength

    if blur_k % 2 == 0:
        blur_k += 1

    # Get face padding - priority: direct param > config
    if face_padding is not None:
        padding = face_padding
    else:
        padding = settings.face_blur_padding

    # Get blur method - priority: direct param > config
    if blur_method is not None:
        blur_method_used = blur_method.lower()
    else:
        blur_method_used = settings.face_blur_method.lower()

    # Validate blur method
    valid_methods = ['gaussian', 'pixelate', 'hybrid']
    if blur_method_used not in valid_methods:
        blur_method_used = 'gaussian'
        logger.warning(f"Invalid blur method '{blur_method}', using 'gaussian'")

    # Get detection confidence - priority: direct param > intensity > config
    if confidence_threshold is not None:
        detect_confidence = confidence_threshold
    elif intensity:
        detect_confidence = settings.get_face_detection_confidence(intensity)
    else:
        detect_confidence = settings.face_detection_confidence

    # Detect faces with appropriate confidence
    detector = get_face_detector(detect_confidence)
    results = detector.process(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))

    faces_detected = 0
    if results.detections:
        for detection in results.detections:
            # Get bounding box
            bbox = detection.location_data.relative_bounding_box
            x_min = max(0, int(bbox.xmin * w) - padding)
            y_min = max(0, int(bbox.ymin * h) - padding)
            x_max = min(w, int((bbox.xmin + bbox.width) * w) + padding)
            y_max = min(h, int((bbox.ymin + bbox.height) * h) + padding)

            # Apply blur to face region
            face_region = cv_image[y_min:y_max, x_min:x_max]

            if blur_method_used == 'pixelate':
                # For pixelation: blur_strength maps to pixel_size (3-20 optimal)
                # 10->3, 50->5, 100->8, 150->12, 200->15
                pixel_size = max(2, min(20, blur_k // 15))
                blurred = apply_pixelation(face_region, pixel_size)
            elif blur_method_used == 'hybrid':
                blurred = apply_hybrid_blur(face_region, blur_k)
            else:  # gaussian (default)
                blurred = apply_gaussian_blur(face_region, blur_k)

            cv_image[y_min:y_max, x_min:x_max] = blurred

            faces_detected += 1

    # Convert back to PIL and then to base64
    result_pil = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
    import PIL.Image
    result_pil = PIL.Image.fromarray(result_pil)
    base64_image = image_to_base64(result_pil)

    response = BlurFacesResponse(
        success=True,
        message=f"Successfully processed image and blurred {faces_detected} face(s)",
        faces_detected=faces_detected,
        processed_image_base64=base64_image,
    )

    logger.info(
        f"Face blur completed - detected: {faces_detected}, "
        f"blur_strength: {blur_k}, confidence: {detect_confidence}, padding: {padding}, "
        f"method: {blur_method_used}"
    )

    return response
