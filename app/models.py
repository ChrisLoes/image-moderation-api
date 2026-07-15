from pydantic import BaseModel, Field
from typing import Optional


class BlurFacesRequest(BaseModel):
    """Request model for face blurring endpoint."""

    blur_strength: Optional[int] = Field(
        default=None,
        ge=1,
        le=50,
        description="Blur kernel size (1-50, must be odd). "
        "Low: 11px (minimal blur), Medium: 25px (standard), High: 41px (heavy blur). "
        "Overrides intensity parameter.",
        example=25,
    )
    confidence_threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Face detection confidence threshold (0.0-1.0). "
        "Lower values detect more faces (including ambiguous ones). "
        "Overrides intensity parameter. "
        "Low: 0.3, Medium: 0.5, High: 0.8",
        example=0.5,
    )
    intensity: Optional[str] = Field(
        default=None,
        description="Detection intensity level. Sets both blur_strength and confidence_threshold. "
        "'low': minimal detection & light blur, 'medium': balanced, 'high': aggressive. "
        "Overridden by explicit blur_strength or confidence_threshold parameters.",
        enum=["low", "medium", "high"],
        example="medium",
    )


class BlurFacesResponse(BaseModel):
    """Response model for face blurring endpoint."""

    success: bool = Field(description="Whether the operation was successful")
    message: str = Field(description="Human-readable status message")
    faces_detected: int = Field(description="Number of faces detected and blurred in the image")
    processed_image_base64: Optional[str] = Field(
        None,
        description="Base64-encoded PNG image with blurred faces. "
        "Use 'data:image/png;base64,' prefix to display in HTML/JS",
    )


class NSFWCheckRequest(BaseModel):
    """Request model for NSFW content checking endpoint."""

    threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="NSFW detection threshold (0.0-1.0). "
        "Images with scores above this are flagged as NSFW. "
        "Overrides intensity parameter. "
        "Low: 0.8 (lenient), Medium: 0.6, High: 0.4 (strict)",
        example=0.6,
    )
    intensity: Optional[str] = Field(
        default=None,
        description="Detection intensity level. Sets the classification threshold. "
        "'low': only obvious NSFW, 'medium': balanced, 'high': aggressive. "
        "Overridden by explicit threshold parameter.",
        enum=["low", "medium", "high"],
        example="medium",
    )
    return_details: Optional[bool] = Field(
        default=False,
        description="Include detailed breakdown of confidence scores for all categories "
        "(safe, partially_nude, nude)",
    )


class NSFWDetection(BaseModel):
    """NSFW detection result for a single category."""

    label: str = Field(description="Category label (safe, partially_nude, nude)")
    confidence: float = Field(description="Confidence score (0.0-1.0)")


class NSFWCheckResponse(BaseModel):
    """Response model for NSFW content checking endpoint."""

    success: bool = Field(description="Whether the analysis was successful")
    is_nsfw: bool = Field(description="Whether image contains NSFW content (based on threshold)")
    confidence: float = Field(
        description="Confidence score of the primary detection (0.0-1.0). "
        "Higher = more confident in that category"
    )
    primary_detection: str = Field(
        description="The category with highest confidence: 'safe', 'partially_nude', or 'nude'"
    )
    detections: Optional[dict[str, float]] = Field(
        None,
        description="Confidence scores for all categories when return_details=true. "
        "Example: {'safe': 0.88, 'partially_nude': 0.08, 'nude': 0.04}",
    )


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str = Field(description="Overall system status (healthy/unhealthy)")
    version: str = Field(description="API version")
    services: dict[str, str] = Field(
        description="Status of individual services. "
        "Values: 'ready', 'unavailable', 'degraded'"
    )


class ErrorResponse(BaseModel):
    """Error response model."""

    detail: str = Field(description="Human-readable error message")
    error_code: Optional[str] = Field(None, description="Machine-readable error code")
