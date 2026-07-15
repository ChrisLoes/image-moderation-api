import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Configuration
    api_keys: str = os.getenv("API_KEYS", "test-key")
    log_level: str = os.getenv("LOG_LEVEL", "info")

    # Face Detection Settings
    face_blur_strength: int = int(os.getenv("FACE_BLUR_STRENGTH", "25"))
    face_detection_confidence: float = float(os.getenv("FACE_DETECTION_CONFIDENCE", "0.5"))
    # Intensity levels: low (0.3), medium (0.5), high (0.8) - can be overridden per request
    face_detection_intensity: str = os.getenv("FACE_DETECTION_INTENSITY", "medium")

    # NSFW Detection Settings
    nsfw_threshold: float = float(os.getenv("NSFW_THRESHOLD", "0.6"))
    # Intensity levels: low (0.8), medium (0.6), high (0.4) - can be overridden per request
    nsfw_detection_intensity: str = os.getenv("NSFW_DETECTION_INTENSITY", "medium")

    # Image Upload Settings
    max_file_size: int = int(os.getenv("MAX_FILE_SIZE", "8388608"))  # 8 MB
    max_image_width: int = int(os.getenv("MAX_IMAGE_WIDTH", "4000"))
    max_image_height: int = int(os.getenv("MAX_IMAGE_HEIGHT", "4000"))

    # Server Settings
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))

    @property
    def valid_api_keys(self) -> set[str]:
        return set(key.strip() for key in self.api_keys.split(",") if key.strip())

    def get_face_detection_confidence(self, intensity: str | None = None) -> float:
        """Get face detection confidence threshold based on intensity level."""
        intensity = intensity or self.face_detection_intensity
        thresholds = {
            "low": 0.3,
            "medium": 0.5,
            "high": 0.8,
        }
        return thresholds.get(intensity.lower(), self.face_detection_confidence)

    def get_nsfw_threshold(self, intensity: str | None = None) -> float:
        """Get NSFW detection threshold based on intensity level."""
        intensity = intensity or self.nsfw_detection_intensity
        thresholds = {
            "low": 0.8,      # More lenient, only flag obvious NSFW
            "medium": 0.6,   # Balanced
            "high": 0.4,     # Aggressive, flag more content
        }
        return thresholds.get(intensity.lower(), self.nsfw_threshold)

    def get_blur_strength(self, intensity: str | None = None) -> int:
        """Get blur strength based on intensity level."""
        intensities = {
            "low": 11,       # Minimal blur
            "medium": 25,    # Standard blur
            "high": 41,      # Heavy blur
        }
        return intensities.get(intensity.lower(), self.face_blur_strength)

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
