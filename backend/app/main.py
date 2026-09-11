"""
CodeSentinel Backend: Main Application Entry Point.

Configures FastAPI application, lifespan events, middleware, global error handlers,
and OpenAPI contract documentation.
"""

import sys
from pathlib import Path

# Ensure project root and backend directory are always on sys.path
_root = Path(__file__).resolve().parent.parent.parent
_backend = Path(__file__).resolve().parent.parent
for _p in [str(_root), str(_backend)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from shared.schemas.common import APIError, APIResponse, utc_now
from app.api.v1.api import api_v1_router
from app.core.config import settings
from app.core.database import init_db
from app.core.envelope import error_response, success_response
from app.core.logging import logger, setup_logging
from app.core.redis import close_redis


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for connection pools and background tasks."""
    setup_logging()
    logger.info("Initializing CodeSentinel Backend (Phase 0: Contract Layer)...")
    logger.info(f"Environment: {settings.ENVIRONMENT} | Debug: {settings.DEBUG}")
    await init_db()
    yield
    logger.info("Shutting down CodeSentinel Backend...")
    await close_redis()


app = FastAPI(
    title="CodeSentinel API",
    version="0.1.0",
    description=(
        "AI-Powered Software Engineering Intelligence Platform Contract Layer. "
        "Provides frozen schemas, AST analysis, knowledge graph relations, "
        "autonomous LangGraph test generation, sandbox execution, and failure triage."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global Exception Handlers ensuring 100% Envelope Compliance
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTPExceptions inside the standard APIResponse envelope."""
    return error_response(
        code=f"HTTP_{exc.status_code}",
        message=str(exc.detail),
        status_code=exc.status_code,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors inside the standard APIResponse envelope."""
    details = {"errors": exc.errors()}
    return error_response(
        code="VALIDATION_ERROR",
        message="Request payload failed schema validation.",
        details=details,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle uncaught server exceptions inside the standard APIResponse envelope."""
    logger.exception(f"Unhandled server error on {request.url.path}: {exc}")
    return error_response(
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected server error occurred.",
        details={"error_type": type(exc).__name__} if settings.DEBUG else None,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


# Root Health & Metadata Endpoints
@app.get(
    "/",
    response_model=APIResponse[dict],
    summary="Root Healthcheck",
    tags=["System"]
)
async def root_health() -> APIResponse[dict]:
    return success_response(
        data={
            "service": settings.PROJECT_NAME,
            "version": "0.1.0",
            "phase": "PHASE_0_CONTRACT_LAYER",
            "status": "HEALTHY",
            "docs": "/docs",
        },
        message="CodeSentinel API is running."
    )


@app.get(
    "/health",
    response_model=APIResponse[dict],
    summary="Liveness and Readiness Probe",
    tags=["System"]
)
async def health_check() -> APIResponse[dict]:
    return success_response(
        data={"status": "UP", "timestamp": utc_now().isoformat()},
        message="Service is healthy."
    )


# Mount API v1 Router
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)
