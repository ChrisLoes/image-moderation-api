from pydantic import BaseModel, Field
from typing import Optional


class BlurFacesRequest(BaseModel):
    blur_strength: Optional[int] = Field(default=None, ge=1, le=50, description="Blur strength (1-50)")
    confidence_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Detection confidence (0.0-1.0)")


class BlurFacesResponse(BaseModel):
    success: bool
    message: str
    faces_detected: int
    processed_image_base64: Optional[str] = Field(None, description="Base64 encoded blurred image")


class NSFWCheckRequest(BaseModel):
    threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="NSFW confidence threshold (0.0-1.0)")
    return_details: Optional[bool] = Field(default=False, description="Return detailed detection breakdown")


class NSFWDetection(BaseModel):
    label: str
    confidence: float


class NSFWCheckResponse(BaseModel):
    success: bool
    is_nsfw: bool
    confidence: float
    primary_detection: str
    detections: Optional[dict[str, float]] = Field(None, description="Detailed breakdown of all detections")


class HealthResponse(BaseModel):
    status: str
    version: str
    services: dict[str, str]


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
