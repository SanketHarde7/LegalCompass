from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from datetime import datetime, timezone
import logging

from app.core.config import settings
from app.api.api_router import api_router
from app.schemas.error import ApiErrorResponse, ApiErrorDetail

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.PROJECT_NAME} on port {settings.PORT}...")
    logger.info(f"Gemini configured: {bool(settings.GEMINI_API_KEY)} (Model: {settings.GEMINI_MODEL_ID})")
    logger.info(f"Groq configured: {bool(settings.GROQ_API_KEY)} (Model: {settings.GROQ_MODEL_ID})")
    yield
    logger.info("Shutting down LegalCompass Backend...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Backend API for LegalCompass: AI contract analysis, What-If simulation, and RAG copilot.",
    lifespan=lifespan,
)

# CORS Configuration
origins = settings.BACKEND_CORS_ORIGINS
if isinstance(origins, str):
    origins = [origins]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if "*" not in origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


# Global Uniform Error Handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    detail = exc.detail
    code = "HTTP_ERROR"
    message = str(detail)

    if isinstance(detail, dict):
        code = detail.get("code", code)
        message = detail.get("message", message)

    error_response = ApiErrorResponse(
        error=ApiErrorDetail(
            code=code,
            message=message,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    )
    return JSONResponse(status_code=exc.status_code, content=error_response.model_dump())


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_response = ApiErrorResponse(
        error=ApiErrorDetail(
            code="INVALID_INPUT",
            message="Validation error on input payload.",
            details={"errors": exc.errors()},
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    )
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=error_response.model_dump())


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error: {exc}", exc_info=True)
    error_response = ApiErrorResponse(
        error=ApiErrorDetail(
            code="INTERNAL_ERROR",
            message="An unexpected server error occurred. Please try again later.",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    )
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=error_response.model_dump())


# Mount Main API Router
app.include_router(api_router, prefix=settings.API_V1_STR)


# Health Check Endpoints
@app.get("/health", tags=["System Health"])
@app.get(f"{settings.API_V1_STR}/health", tags=["System Health"])
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project": settings.PROJECT_NAME,
        "gemini_model_id": settings.GEMINI_MODEL_ID,
        "groq_model_id": settings.GROQ_MODEL_ID,
        "providers": {
            "gemini": {
                "configured": bool(settings.GEMINI_API_KEY),
                "model_id": settings.GEMINI_MODEL_ID,
            },
            "groq": {
                "configured": bool(settings.GROQ_API_KEY),
                "model_id": settings.GROQ_MODEL_ID,
            },
        },
    }


# -----------------------------------------------------------------------------
# Frontend Static Files & SPA Fallback (Enables Single Web Service Deployment)
# -----------------------------------------------------------------------------
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

possible_dist_dirs = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "dist")),
    os.path.abspath(os.path.join(os.getcwd(), "dist")),
    os.path.abspath("dist"),
]

dist_dir = next(
    (d for d in possible_dist_dirs if os.path.isdir(d) and os.path.exists(os.path.join(d, "index.html"))),
    None,
)

if dist_dir:
    logger.info(f"Mounted frontend static directory: {dist_dir}")
    assets_dir = os.path.join(dist_dir, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        if full_path.startswith("api/") or full_path == "api":
            return JSONResponse(status_code=404, content={"detail": "Not Found"})
        file_path = os.path.join(dist_dir, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(dist_dir, "index.html"))

