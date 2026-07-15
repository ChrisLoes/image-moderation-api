import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from app.config import settings
from app.models import HealthResponse
from app.routers import faces, nsfw

# Configure logging
logging.basicConfig(level=settings.log_level.upper())
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="MediaPipe NSFW Detection API",
    description="API for face detection/blurring and NSFW content detection",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(faces.router)
app.include_router(nsfw.router)


@app.get("/health", response_model=HealthResponse, summary="Health check")
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns status of API and all services.
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        services={
            "face_detection": "ready",
            "nsfw_detection": "ready",
        },
    )


@app.get("/", summary="API Root")
async def root():
    """Welcome endpoint."""
    return {
        "message": "MediaPipe NSFW Detection API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
    }


# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="MediaPipe NSFW Detection API",
        version="1.0.0",
        description="API for face detection/blurring and NSFW content detection",
        routes=app.routes,
    )
    openapi_schema["info"]["x-logo"] = {
        "url": "https://www.gstatic.com/devrel-devsite/prod/v2210deb39920cd4a55bd580441aa58e853afc04b39a9d9ac4198e1cd7fbe04ef/tensorflow/images/favicon.ico"
    }
    # Add API Key security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API Key for authentication",
        }
    }
    # Apply security to all endpoints
    for path in openapi_schema["paths"].values():
        for operation in path.values():
            if isinstance(operation, dict):
                operation.setdefault("security", []).append({"ApiKeyAuth": []})

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
    )
