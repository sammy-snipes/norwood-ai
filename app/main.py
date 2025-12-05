import base64
import logging
from pathlib import Path as FilePath

from fastapi import FastAPI, File, HTTPException, Path, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette import status as http_status

from app.celery_worker import celery_app
from app.config import get_settings
from app.routers import auth_router
from app.schemas import AnalyzeResponse, HealthResponse, TaskResponse, TaskStatusResponse
from app.tasks.analyze import analyze_image_task

settings = get_settings()

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

logger.info(f"[DEBUG] API key configured: {bool(settings.ANTHROPIC_API_KEY)}")
logger.info(f"[DEBUG] Allowed origins: {settings.ALLOWED_ORIGINS}")
logger.info(f"[DEBUG] Celery broker: {settings.CELERY_BROKER_URL}")

app = FastAPI(
    title="Norwood AI",
    description="API for classifying hair loss using the Norwood scale",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)

# Serve static frontend files if they exist (built Vue app)
STATIC_DIR = FilePath(__file__).parent.parent / "frontend" / "dist"
if STATIC_DIR.exists():
    logger.info(f"[DEBUG] Serving static files from {STATIC_DIR}")
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")
    if (STATIC_DIR / "img").exists():
        app.mount("/img", StaticFiles(directory=STATIC_DIR / "img"), name="img")


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="healthy", version="0.1.0")


@app.post(
    "/analyze",
    response_model=TaskResponse,
    status_code=http_status.HTTP_202_ACCEPTED,
)
async def submit_analysis(
    file: UploadFile = File(..., description="Image file to analyze"),
) -> TaskResponse:
    """
    Submit an image for Norwood scale analysis.

    Returns a task_id that can be polled for results.
    """
    logger.info(f"[DEBUG] Received analyze request - file: {file.filename}, type: {file.content_type}")

    # Validate file type
    if file.content_type not in [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
    ]:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image type: {file.content_type}. Use JPEG, PNG, GIF, or WebP.",
        )

    # Read and validate file size
    contents = await file.read()
    if len(contents) > settings.max_image_size_bytes:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Image too large. Maximum size is {settings.MAX_IMAGE_SIZE_MB}MB.",
        )

    # Encode image to base64
    image_base64 = base64.standard_b64encode(contents).decode("utf-8")
    logger.info(f"[DEBUG] Image encoded, submitting task...")

    # Submit task to Celery
    task = analyze_image_task.apply_async(
        args=[image_base64, file.content_type]
    )

    logger.info(f"[DEBUG] Task submitted: {task.id}")
    return TaskResponse(task_id=task.id, status="pending")


@app.get(
    "/tasks/{task_id}",
    response_model=TaskStatusResponse,
)
def get_task_status(
    task_id: str = Path(..., description="Task ID to check"),
) -> TaskStatusResponse:
    """
    Get the status of an analysis task.

    Poll this endpoint until status is 'completed' or 'failed'.
    """
    task_result = celery_app.AsyncResult(task_id)

    response = TaskStatusResponse(
        task_id=task_id,
        status=task_result.state.lower(),
        ready=task_result.ready(),
    )

    if task_result.ready():
        if task_result.successful():
            result = task_result.result
            if result.get("success"):
                response.status = "completed"
                response.result = AnalyzeResponse(
                    success=True,
                    analysis=result["analysis"],
                )
            else:
                response.status = "failed"
                response.error = result.get("error", "Unknown error")
        else:
            response.status = "failed"
            response.error = str(task_result.info)

    return response


# Catch-all route to serve Vue SPA (must be last)
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """Serve the Vue SPA for any non-API routes."""
    index_file = STATIC_DIR / "index.html"
    if STATIC_DIR.exists() and index_file.exists():
        return FileResponse(index_file)
    raise HTTPException(status_code=404, detail="Frontend not built. Run 'make build-frontend'")
