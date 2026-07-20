import logging
import logging.handlers
import os
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from app.config import settings
from app.models import HealthResponse
from app.routers import faces, nsfw

# Setup logging directory
os.makedirs("logs", exist_ok=True)

# Configure logging with both console and file output
log_level = settings.log_level.upper()
log_format = logging.Formatter(
    fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Root logger
root_logger = logging.getLogger()
root_logger.setLevel(log_level)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(log_level)
console_handler.setFormatter(log_format)
root_logger.addHandler(console_handler)

# File handler (rotating, max 10 files of 10 MB each)
file_handler = logging.handlers.RotatingFileHandler(
    "logs/api.log",
    maxBytes=10 * 1024 * 1024,  # 10 MB
    backupCount=10,
)
file_handler.setLevel(log_level)
file_handler.setFormatter(log_format)
root_logger.addHandler(file_handler)

# Separate error log file
error_handler = logging.handlers.RotatingFileHandler(
    "logs/error.log",
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
)
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(log_format)
root_logger.addHandler(error_handler)

logger = logging.getLogger(__name__)
logger.info(f"Logging configured at level: {log_level}")

# Lifespan context manager (defined after logger)
@asynccontextmanager
async def lifespan_handler(app: FastAPI):
    """Manage application lifespan (startup and shutdown)."""
    # Startup
    logger.info("=" * 60)
    logger.info("MediaPipe NSFW Detection API Starting")
    logger.info("=" * 60)
    logger.info(f"API Version: 1.0.0")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'production')}")
    logger.info(f"Log Level: {log_level}")
    logger.info(f"Face Detection Intensity: {settings.face_detection_intensity}")
    logger.info(f"NSFW Detection Intensity: {settings.nsfw_detection_intensity}")
    logger.info("=" * 60)

    yield

    # Shutdown
    logger.info("=" * 60)
    logger.info("MediaPipe NSFW Detection API Shutting Down")
    logger.info("=" * 60)


# Create FastAPI app
app = FastAPI(
    title="MediaPipe NSFW Detection API",
    description="API for face detection/blurring and NSFW content detection",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan_handler,
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests and outgoing responses."""
    request_id = str(time.time()).replace(".", "")[:12]

    # Log incoming request
    logger.info(
        f"[{request_id}] {request.method} {request.url.path} - "
        f"Client: {request.client.host if request.client else 'unknown'}"
    )

    start_time = time.time()

    try:
        response = await call_next(request)
        process_time = time.time() - start_time

        # Log outgoing response
        logger.info(
            f"[{request_id}] Response {response.status_code} - "
            f"Duration: {process_time:.3f}s"
        )

        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"[{request_id}] Request failed after {process_time:.3f}s - "
            f"Error: {str(e)}",
            exc_info=True,
        )
        raise


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


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check API and service health status. "
    "Use this endpoint for monitoring and load balancer health checks.",
    responses={
        200: {
            "description": "System is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "version": "1.0.0",
                        "services": {
                            "face_detection": "ready",
                            "nsfw_detection": "ready",
                        },
                    }
                }
            },
        },
    },
    tags=["System"],
)
async def health_check() -> HealthResponse:
    """
    Check API and service availability.

    ## Response Status Values
    - **healthy**: All services operational
    - **degraded**: Some services unavailable but core functionality works
    - **unhealthy**: Critical services unavailable

    ## Service Status Values
    - **ready**: Service available and responding
    - **unavailable**: Service not available (e.g., model missing)
    - **degraded**: Service available but operating at reduced capacity

    This endpoint does not require authentication and can be used for:
    - Kubernetes/Docker health checks
    - Load balancer probes
    - Monitoring dashboards
    - Readiness/liveness checks
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        services={
            "face_detection": "ready",
            "nsfw_detection": "ready",
        },
    )


@app.get(
    "/",
    summary="API Welcome",
    description="Root endpoint with API information and documentation links.",
    tags=["System"],
)
async def root():
    """
    Welcome to MediaPipe NSFW Detection API.

    ## Available Endpoints
    - **Face Detection & Blurring**: `POST /faces/blur` - Detect and blur faces
    - **NSFW Content Detection**: `POST /nsfw/check` - Analyze images for adult content
    - **Health Check**: `GET /health` - System status
    - **Documentation**: `/docs` (Swagger UI), `/redoc` (ReDoc)

    ## Quick Start
    1. Use API key from `X-API-Key` header
    2. POST image file to `/faces/blur` or `/nsfw/check`
    3. Receive JSON response with results

    See `/docs` for interactive API explorer.
    """
    return {
        "message": "MediaPipe NSFW Detection API",
        "version": "1.0.0",
        "docs": "/docs (Swagger UI)",
        "redoc": "/redoc (ReDoc documentation)",
        "endpoints": {
            "faces": "/faces/blur (POST)",
            "nsfw": "/nsfw/check (POST)",
            "health": "/health (GET)",
        },
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
