import cv2
import numpy as np
import mediapipe as mp
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from typing import Optional
from app.auth import verify_api_key
from app.models import BlurFacesRequest, BlurFacesResponse
from app.utils import validate_image, image_to_base64
from app.config import settings

router = APIRouter(prefix="/faces", tags=["Face Detection"])

mp_face_detection = mp.solutions.face_detection
face_detector = None


def get_face_detector():
    """Lazy load face detector."""
    global face_detector
    if face_detector is None:
        face_detector = mp_face_detection.FaceDetection(
            model_selection=0, min_detection_confidence=settings.face_detection_confidence
        )
    return face_detector


@router.post(
    "/blur",
    response_model=BlurFacesResponse,
    summary="Blur faces in image",
    description="Detect and blur all faces in the provided image",
)
async def blur_faces(
    file: UploadFile = File(..., description="Image file (JPEG, PNG, GIF, WebP)"),
    blur_strength: Optional[int] = None,
    confidence_threshold: Optional[float] = None,
    api_key: str = Depends(verify_api_key),
) -> BlurFacesResponse:
    """
    Detect faces in image and apply blur effect.

    **Parameters:**
    - `blur_strength`: Blur kernel size (1-50, default from config)
    - `confidence_threshold`: Face detection confidence (0.0-1.0, overrides config)
    """
    # Validate image
    pil_image = await validate_image(file)

    # Convert PIL Image to OpenCV format
    cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    h, w = cv_image.shape[:2]

    # Get blur parameters
    blur_k = blur_strength or settings.face_blur_strength
    if blur_k % 2 == 0:
        blur_k += 1

    # Detect faces
    detector = get_face_detector()
    results = detector.process(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))

    faces_detected = 0
    if results.detections:
        for detection in results.detections:
            # Get bounding box
            bbox = detection.location_data.relative_bounding_box
            x_min = max(0, int(bbox.xmin * w) - 10)
            y_min = max(0, int(bbox.ymin * h) - 10)
            x_max = min(w, int((bbox.xmin + bbox.width) * w) + 10)
            y_max = min(h, int((bbox.ymin + bbox.height) * h) + 10)

            # Apply blur to face region
            face_region = cv_image[y_min:y_max, x_min:x_max]
            blurred = cv2.blur(face_region, (blur_k, blur_k))
            cv_image[y_min:y_max, x_min:x_max] = blurred

            faces_detected += 1

    # Convert back to PIL and then to base64
    result_pil = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
    import PIL.Image
    result_pil = PIL.Image.fromarray(result_pil)
    base64_image = image_to_base64(result_pil)

    return BlurFacesResponse(
        success=True,
        message=f"Successfully processed image and blurred {faces_detected} face(s)",
        faces_detected=faces_detected,
        processed_image_base64=base64_image,
    )
