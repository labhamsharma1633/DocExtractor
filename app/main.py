import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import logger, setup_logging
from app.db.base import Base
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle management."""
    setup_logging()
    logger.info(f"Starting {settings.PROJECT_NAME} in {settings.ENVIRONMENT} mode...")
    # Initialize DB tables (for development/testing environments)
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema verified and synchronized.")
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="Scalable Document Processing & Question Extraction Service backend.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handles all custom application exceptions with uniform JSON output."""
    logger.warning(f"AppException on {request.method} {request.url.path}: {exc.message} (status: {exc.status_code})")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.message,
                "status_code": exc.status_code,
                "details": exc.details,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handles Pydantic request validation errors."""
    logger.warning(f"Validation error on {request.method} {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "message": "Input validation error",
                "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                "details": exc.errors(),
            }
        },
    )


@app.api_route("/health", methods=["GET", "HEAD"], tags=["Health"])
async def health_check():
    """Health check endpoint to verify system availability."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "environment": settings.ENVIRONMENT,
    }


# Include API v1 routes
from app.api.v1.router import api_router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Serve page images directory if present
if os.path.exists(settings.PAGE_IMAGE_DIR):
    app.mount("/page_images", StaticFiles(directory=settings.PAGE_IMAGE_DIR), name="page_images")

# Serve Samples directory if present
if os.path.exists("samples"):
    app.mount("/samples", StaticFiles(directory="samples"), name="samples")

# Serve UI Static Files
if os.path.exists("static"):
    app.mount("/dashboard", StaticFiles(directory="static", html=True), name="static")


@app.api_route("/", methods=["GET", "HEAD"], tags=["UI"])
async def root():
    """Redirect root path to interactive visual dashboard."""
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "docs": "/docs",
        "api_v1": settings.API_V1_STR,
    }
