"""CV service application — ONNX inference microservice.

Phase 3: Real ONNX inference microservice with:
- GET /healthz
- GET /models
- POST /predict (multipart image -> food classification, freshness, and hazard assessment)
"""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import JSONResponse
from PIL import Image

from app.pipeline import InferencePipeline

logger = logging.getLogger(__name__)

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
APP_ENV = os.environ.get("APP_ENV", "development")
APP_VERSION = os.environ.get("APP_VERSION", "0.1.0")
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_MB", "10")) * 1024 * 1024


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        stream=sys.stdout,
        format='{"ts":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}',
    )
    logger.info("Initializing CV inference pipeline...")
    pipeline = InferencePipeline()
    app.state.pipeline = pipeline
    logger.info("CV service ready with models: %s", pipeline.model_versions)
    yield
    logger.info("CV service shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="BountyLoop CV Service",
        description="ONNX inference microservice: food item classification, freshness grading, hazard detection.",
        version=APP_VERSION,
        lifespan=lifespan,
    )

    # ── Exception handlers (RFC-7807 problem+json) ────────────────────────────
    @app.exception_handler(HTTPException)
    async def _http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        titles = {
            400: "Bad Request",
            404: "Not Found",
            413: "Payload Too Large",
            415: "Unsupported Media Type",
            500: "Internal Server Error",
        }
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "type": "about:blank",
                "title": titles.get(exc.status_code, "HTTP Error"),
                "status": exc.status_code,
                "detail": exc.detail,
                "instance": str(request.url),
            },
            media_type="application/problem+json",
        )

    @app.get("/healthz", tags=["ops"], summary="Liveness probe")
    async def healthz(request: Request) -> dict:
        pipeline: InferencePipeline = getattr(request.app.state, "pipeline", None)
        models = pipeline.model_versions if pipeline else {}
        return {
            "status": "ok",
            "version": APP_VERSION,
            "env": APP_ENV,
            "models_loaded": models,
        }

    @app.get("/models", tags=["ops"], summary="List loaded model versions")
    async def models(request: Request) -> dict:
        pipeline: InferencePipeline = getattr(request.app.state, "pipeline", None)
        models = pipeline.model_versions if pipeline else {}
        return {"models": models}

    @app.post("/predict", tags=["inference"], summary="Classify food image")
    async def predict(
        request: Request,
        file: UploadFile = File(...),  # noqa: B008
        tta: bool | None = Query(
            default=None, description="Enable test-time augmentation"
        ),
    ) -> JSONResponse:
        """Run food item, freshness, and safety hazard classification on uploaded image."""
        pipeline: InferencePipeline = getattr(request.app.state, "pipeline", None)
        if pipeline is None:
            pipeline = InferencePipeline()
            request.app.state.pipeline = pipeline

        # 1. Read file bytes and check empty
        contents = await file.read()
        if not contents or len(contents) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty image file provided.",
            )

        # 2. Check maximum size (10 MB)
        if len(contents) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"Image size exceeds limit of {MAX_UPLOAD_BYTES // (1024*1024)} MB.",
            )

        # 3. Verify valid image structure
        import io

        try:
            with Image.open(io.BytesIO(contents)) as test_img:
                test_img.verify()
        except (OSError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unreadable or unsupported image format.",
            )

        # 4. Execute prediction pipeline
        try:
            result = pipeline.predict(contents, apply_tta=tta)
        except Exception:
            logger.exception("Inference execution failed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Inference execution failed.",
            )

        return JSONResponse(status_code=200, content=result)

    return app


app = create_app()
