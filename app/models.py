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
        "Low: 0.8, Medium: 0.5, High: 0.3",
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
        json_schema_extra={"enum": ["low", "medium", "high"], "example": "medium"},
    )
    return_details: Optional[bool] = Field(
        default=False,
        description="Include detailed breakdown of confidence scores for all categories "
        "(safe, partially_nude, nude, offensive_gesture) and the individual findings",
    )


class NSFWDetection(BaseModel):
    """A single finding in the image (body part or hand gesture)."""

    label: str = Field(
        description="What was found, e.g. 'FEMALE_BREAST_EXPOSED' (NudeNet class) or 'middle_finger'"
    )
    category: str = Field(description="Category the finding counts towards: nude, partially_nude, offensive_gesture")
    confidence: float = Field(description="Confidence score (0.0-1.0)")
    box: list[int] = Field(description="Bounding box in pixels: [x, y, width, height]")


class NSFWCheckResponse(BaseModel):
    """Response model for NSFW content checking endpoint."""

    success: bool = Field(description="Whether the analysis was successful")
    is_nsfw: bool = Field(description="Whether image contains NSFW content (nsfw_score above the threshold)")
    nsfw_score: float = Field(
        description="Overall score (0.0-1.0) how likely the image is not safe for work. "
        "Highest of: nude score, offensive gesture score and half the partially_nude score "
        "(swimwear/underwear alone never exceeds 0.5). Compare against your own threshold."
    )
    confidence: float = Field(
        description="Confidence score of the primary detection (0.0-1.0). "
        "Higher = more confident in that category"
    )
    primary_detection: str = Field(
        description="The category with highest score: 'safe', 'partially_nude', 'nude' or 'offensive_gesture'"
    )
    reasons: list[str] = Field(
        default_factory=list,
        description="Categories that exceeded the threshold, e.g. ['nude', 'offensive_gesture']. Empty if safe.",
    )
    detections: Optional[dict[str, float]] = Field(
        None,
        description="Scores for all categories when return_details=true. "
        "Example: {'safe': 0.88, 'partially_nude': 0.08, 'nude': 0.04, 'offensive_gesture': 0.0}",
    )
    findings: Optional[list[NSFWDetection]] = Field(
        None,
        description="Individual findings with boxes when return_details=true",
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
