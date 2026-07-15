import numpy as np
import onnxruntime as ort
from PIL import Image
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from typing import Optional
import logging
from app.auth import verify_api_key
from app.models import NSFWCheckRequest, NSFWCheckResponse
from app.utils import validate_image
from app.config import settings

router = APIRouter(prefix="/nsfw", tags=["NSFW Detection"])
logger = logging.getLogger(__name__)

nsfw_model = None


def get_nsfw_detector():
    """
    Lazy load NSFW detector using NudeNet v3 (ONNX).

    For production, download the model:
    https://github.com/notAI-tech/NudeNet/releases/tag/v3
    """
    global nsfw_model
    if nsfw_model is None:
        try:
            model_path = "models/classifier_nsfw.onnx"
            providers = ["TensorrtExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider"]
            nsfw_model = ort.InferenceSession(model_path, providers=providers)
        except FileNotFoundError:
            logger.warning("NSFW model not found at models/classifier_nsfw.onnx")
            logger.info("Download from: https://github.com/notAI-tech/NudeNet/releases/tag/v3")
            nsfw_model = None
        except Exception as e:
            logger.error(f"Failed to load NSFW model: {str(e)}")
            nsfw_model = None
    return nsfw_model


def prepare_image_for_nsfw(image: Image.Image) -> np.ndarray:
    """Prepare image for NudeNet v3 model (usually 224x224 input)."""
    # Resize to model input size
    image = image.resize((224, 224), Image.Resampling.LANCZOS)

    # Convert to numpy array and normalize
    img_array = np.array(image, dtype=np.float32)

    # Normalize (ImageNet normalization)
    img_array = img_array / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    img_array = (img_array - mean) / std

    # Add batch dimension: (1, 3, 224, 224) - NCHW format expected by ONNX
    img_array = np.transpose(img_array, (2, 0, 1))
    img_array = np.expand_dims(img_array, axis=0)

    return img_array


@router.post(
    "/check",
    response_model=NSFWCheckResponse,
    summary="Check image for NSFW content",
    description="Analyze image for NSFW content using NudeNet v3",
)
async def check_nsfw(
    file: UploadFile = File(..., description="Image file (JPEG, PNG, GIF, WebP)"),
    threshold: Optional[float] = None,
    return_details: Optional[bool] = False,
    api_key: str = Depends(verify_api_key),
) -> NSFWCheckResponse:
    """
    Detect NSFW content in image.

    **Parameters:**
    - `threshold`: Confidence threshold for NSFW classification (0.0-1.0, default from config)
    - `return_details`: Include detailed breakdown of all detections

    **Returns:**
    - `is_nsfw`: Boolean indicating if image contains NSFW content
    - `confidence`: Confidence score for the primary detection
    - `primary_detection`: The primary category detected
    - `detections`: (optional) Detailed breakdown of all categories
    """
    # Validate image
    pil_image = await validate_image(file)

    # Get model
    model = get_nsfw_detector()
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NSFW detection model not loaded. Ensure models/classifier_nsfw.onnx exists.",
        )

    try:
        # Prepare image
        prepared_image = prepare_image_for_nsfw(pil_image)

        # Get model input/output names
        input_name = model.get_inputs()[0].name
        output_name = model.get_outputs()[0].name

        # Run inference
        predictions = model.run([output_name], {input_name: prepared_image})[0]

        # Parse results (NudeNet v3 typically returns probabilities for multiple categories)
        # Common categories: ['nude', 'partially_nude', 'safe']
        # Adjust based on your specific model version
        predictions = predictions[0]

        # Get threshold
        decision_threshold = threshold or settings.nsfw_threshold

        # Determine if NSFW (adjust category indices based on your model)
        # Typical: index 0 = safe, index 1 = partially_nude, index 2 = nude
        is_nsfw = max(predictions[1:]) > decision_threshold if len(predictions) > 1 else predictions[0] > decision_threshold

        # Get primary detection
        categories = ["safe", "partially_nude", "nude"]
        primary_idx = np.argmax(predictions)
        primary_detection = categories[primary_idx] if primary_idx < len(categories) else "unknown"
        confidence = float(predictions[primary_idx])

        detections = None
        if return_details:
            detections = {cat: float(pred) for cat, pred in zip(categories, predictions)}

        return NSFWCheckResponse(
            success=True,
            is_nsfw=bool(is_nsfw),
            confidence=confidence,
            primary_detection=primary_detection,
            detections=detections,
        )

    except Exception as e:
        logger.error(f"Error during NSFW detection: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing image: {str(e)}",
        )
