import base64
import io
import logging
from PIL import Image
from fastapi import UploadFile, HTTPException, status
from app.config import settings

logger = logging.getLogger(__name__)

# Register HEIF opener for PIL
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    logger.info("HEIF/HEIC support enabled via pillow-heif")
except ImportError:
    logger.warning("pillow-heif not installed - HEIF/HEIC support unavailable")

ALLOWED_FORMATS = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/heif",
    "image/heic",
}
MAGIC_NUMBERS = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89\x50\x4e\x47": "image/png",
    b"\x47\x49\x46\x38": "image/gif",
    b"\x52\x49\x46\x46": "image/webp",
    b"\x00\x00\x00\x18ftypheif": "image/heif",  # HEIF
    b"\x00\x00\x00\x18ftypheic": "image/heic",  # HEIC
}


async def validate_image(file: UploadFile) -> Image.Image:
    """
    Validate image file format, size, and dimensions.

    Returns PIL Image object.
    Raises HTTPException if validation fails.
    """
    # Check MIME type
    if file.content_type and file.content_type not in ALLOWED_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image format. Allowed: JPEG, PNG, GIF, WebP, HEIF, HEIC (iPhone)",
        )

    logger.debug(f"Image validation started - file: {file.filename}, type: {file.content_type}")

    # Read file content
    contents = await file.read()

    # Check file size
    file_size = len(contents)
    if file_size > settings.max_file_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds limit ({settings.max_file_size / 1024 / 1024:.1f} MB)",
        )

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty",
        )

    # Validate magic number
    is_valid_format = any(contents.startswith(magic) for magic in MAGIC_NUMBERS.keys())
    if not is_valid_format:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file or corrupted file",
        )

    # Open and validate with PIL
    try:
        image = Image.open(io.BytesIO(contents))
        image.load()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot process image file: {str(e)}",
        )

    # Check dimensions
    width, height = image.size
    if width > settings.max_image_width or height > settings.max_image_height:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image dimensions exceed limit ({settings.max_image_width}x{settings.max_image_height}px)",
        )

    # Convert to RGB if necessary (for JPEG compatibility)
    if image.mode in ("RGBA", "LA", "P"):
        rgb_image = Image.new("RGB", image.size, (255, 255, 255))
        rgb_image.paste(image, mask=image.split()[-1] if image.mode in ("RGBA", "LA") else None)
        return rgb_image

    if image.mode != "RGB":
        image = image.convert("RGB")

    return image


def image_to_base64(image: Image.Image) -> str:
    """Convert PIL Image to base64 string."""
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG", quality=95)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str
