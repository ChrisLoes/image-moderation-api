from fastapi import Header, HTTPException, status
from app.config import settings


async def verify_api_key(x_api_key: str | None = Header(None, alias="X-API-Key")) -> str:
    """
    Verify API key from request header.

    Raises HTTPException if key is invalid.
    """
    if not x_api_key or x_api_key not in settings.valid_api_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return x_api_key
