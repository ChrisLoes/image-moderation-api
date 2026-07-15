import numpy as np
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
            import onnxruntime as ort

            model_path = "models/classifier_nsfw.onnx"
            providers = ["TensorrtExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider"]
            nsfw_model = ort.InferenceSession(model_path, providers=providers)
        except FileNotFoundError:
            logger.warning("NSFW model not found at models/classifier_nsfw.onnx")
            logger.info("Download from: https://github.com/notAI-tech/NudeNet/releases/tag/v3")
            nsfw_model = None
        except ImportError as e:
            logger.error(f"ONNX Runtime not available: {str(e)}")
            logger.warning("NSFW detection will not be available")
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
    description="Analyze image for NSFW content using NudeNet v3 ONNX model. "
    "Returns classification confidence scores and boolean flag for easy content filtering.",
    responses={
        200: {
            "description": "Successfully analyzed image",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "is_nsfw": False,
                        "confidence": 0.88,
                        "primary_detection": "safe",
                        "detections": {"safe": 0.88, "partially_nude": 0.08, "nude": 0.04},
                    }
                }
            },
        },
        400: {"description": "Invalid image format or dimensions"},
        401: {"description": "Missing or invalid API key"},
        413: {"description": "File too large (exceeds MAX_FILE_SIZE)"},
        503: {"description": "NSFW model not loaded (models/classifier_nsfw.onnx missing)"},
    },
)
async def check_nsfw(
    file: UploadFile = File(
        ...,
        description="Image file to analyze (JPEG, PNG, GIF, WebP). Max 8 MB, max 4000×4000 px.",
    ),
    intensity: Optional[str] = None,
    threshold: Optional[float] = None,
    return_details: Optional[bool] = False,
    api_key: str = Depends(verify_api_key),
) -> NSFWCheckResponse:
    """
    Detect NSFW content in image.

    ## How It Works
    1. Receives image file and configuration parameters
    2. Resizes image to 224×224 for NudeNet model input
    3. Applies ImageNet normalization
    4. Runs ONNX inference on pre-trained NudeNet classifier
    5. Returns classification results with confidence scores

    ## Categories
    - **safe**: Image contains no nudity or sexual content
    - **partially_nude**: Image contains partial nudity or suggestive content
    - **nude**: Image contains full nudity or explicit content

    ## Parameter Priority (highest to lowest)
    1. Explicit `threshold` parameter
    2. `intensity` level (low/medium/high)
    3. Environment/config defaults

    ## Intensity Levels
    - **low**: Threshold=0.8 (lenient, only flag obvious NSFW) - Good for UGC
    - **medium**: Threshold=0.6 (balanced) - Recommended default
    - **high**: Threshold=0.4 (strict, flags questionable content) - For child safety/compliance

    ## Return Details
    - Without `return_details`: Only returns primary category + overall decision
    - With `return_details=true`: Returns confidence scores for all categories

    ## Examples
    - Basic check: `POST /nsfw/check -F "file=@image.jpg"`
    - Detailed results: `POST /nsfw/check -F "file=@image.jpg" -F "return_details=true"`
    - High intensity: `POST /nsfw/check -F "file=@image.jpg" -F "intensity=high"`
    - Custom threshold: `POST /nsfw/check -F "file=@image.jpg" -F "threshold=0.5"`

    ## Model Info
    - **Model**: NudeNet v3 ONNX
    - **Input**: 224×224 RGB image (normalized)
    - **Output**: 3-class probabilities (safe, partially_nude, nude)
    - **Download**: https://github.com/notAI-tech/NudeNet/releases/tag/v3
    """
    logger.debug(
        f"NSFW check request - intensity: {intensity}, threshold: {threshold}, "
        f"return_details: {return_details}"
    )

    # Validate image
    pil_image = await validate_image(file)
    logger.debug(f"Image validated - size: {pil_image.size}")

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

        # Get threshold - priority: direct param > intensity > config
        if threshold is not None:
            decision_threshold = threshold
        elif intensity:
            decision_threshold = settings.get_nsfw_threshold(intensity)
        else:
            decision_threshold = settings.nsfw_threshold

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

        response = NSFWCheckResponse(
            success=True,
            is_nsfw=bool(is_nsfw),
            confidence=confidence,
            primary_detection=primary_detection,
            detections=detections,
        )

        log_level = logging.WARNING if is_nsfw else logging.INFO
        logger.log(
            log_level,
            f"NSFW check completed - is_nsfw: {is_nsfw}, "
            f"primary: {primary_detection}, confidence: {confidence:.3f}, "
            f"threshold: {decision_threshold}",
        )

        return response

    except Exception as e:
        logger.error(f"Error during NSFW detection: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing image: {str(e)}",
        )
