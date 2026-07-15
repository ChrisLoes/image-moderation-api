import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Configuration
    api_keys: str = os.getenv("API_KEYS", "test-key")
    log_level: str = os.getenv("LOG_LEVEL", "info")

    # Face Detection Settings
    face_blur_strength: int = int(os.getenv("FACE_BLUR_STRENGTH", "25"))
    face_detection_confidence: float = float(os.getenv("FACE_DETECTION_CONFIDENCE", "0.5"))

    # NSFW Detection Settings
    nsfw_threshold: float = float(os.getenv("NSFW_THRESHOLD", "0.6"))

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

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
