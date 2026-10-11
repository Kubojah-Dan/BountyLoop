"""CV service application — ONNX inference microservice.

Phase 0: provides /healthz (live) and a stub POST /predict (returns 501).
Phase 3: stub is replaced with real ONNX inference.
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
APP_ENV = os.environ.get("APP_ENV", "development")
APP_VERSION = os.environ.get("APP_VERSION", "0.1.0")

# Model version metadata — updated in Phase 3 when real models are loaded
_MODEL_VERSIONS: dict[str, str] = {}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    import sys

    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        stream=sys.stdout,
        format='{"ts":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}',
    )
    logger.info("CV service starting (Phase 0 — stub mode, no ONNX models loaded)")
    # Phase 3: load ONNX sessions here
    yield
    logger.info("CV service shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="BountyLoop CV Service",
        description="ONNX inference microservice: food item classification, freshness grading, hazard detection.",
        version=APP_VERSION,
        lifespan=lifespan,
    )

    @app.get("/healthz", tags=["ops"], summary="Liveness probe")
    async def healthz() -> dict:
        return {
            "status": "ok",
            "version": APP_VERSION,
            "env": APP_ENV,
            "models_loaded": _MODEL_VERSIONS,
        }

    @app.get("/models", tags=["ops"], summary="List loaded model versions")
    async def models() -> dict:
        return {"models": _MODEL_VERSIONS}

    @app.post("/predict", tags=["inference"], summary="Classify food image")
    async def predict(file: UploadFile = File(...)) -> JSONResponse:
        """
        Phase 0 stub — returns 501 Not Implemented.
        This endpoint will be replaced in Phase 3 with real ONNX inference.

        Expected Phase 3+ response schema:
        {
            "item": str,                    # 12-category taxonomy
            "item_confidence": float,
            "freshness": str,               # fresh | spoiled (v1)
            "freshness_confidence": float,
            "hazard_flag": str,             # none | suspected_contamination_or_formalin
            "needs_review": bool,
            "model_versions": {str: str},
            "latency_ms": float
        }
        """
        logger.warning(
            "POST /predict called in stub mode (Phase 0). "
            "Train models and replace this stub in Phase 3."
        )
        return JSONResponse(
            status_code=501,
            content={
                "type": "about:blank",
                "title": "Not Implemented",
                "status": 501,
                "detail": (
                    "CV inference is not yet implemented (Phase 0 stub). "
                    "This endpoint will return real predictions after Phase 3 model training."
                ),
            },
            media_type="application/problem+json",
        )

    return app


app = create_app()
