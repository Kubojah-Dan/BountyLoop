"""BountyLoop FastAPI application factory."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import orjson
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import RequestIdMiddleware, configure_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown logic."""
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info(
        "BountyLoop API starting",
        extra={"version": settings.app_version, "env": settings.app_env},
    )
    yield
    logger.info("BountyLoop API shutting down")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="BountyLoop API",
        description=(
            "AI-powered food rescue and redistribution platform. "
            "Turn surplus into supper — the AI loop that keeps good food in the community."
        ),
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── Middleware ─────────────────────────────────────────────────────────────
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Global exception handler (RFC-7807 problem+json) ──────────────────────
    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception", exc_info=exc)
        body = orjson.dumps(
            {
                "type": "about:blank",
                "title": "Internal Server Error",
                "status": 500,
                "detail": "An unexpected error occurred.",
            }
        )
        return JSONResponse(
            content=orjson.loads(body),
            status_code=500,
            media_type="application/problem+json",
        )

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/healthz", tags=["ops"], summary="Liveness probe")
    async def healthz() -> dict:
        return {
            "status": "ok",
            "version": settings.app_version,
            "env": settings.app_env,
        }

    # ── API v1 router (added in Phase 2) ──────────────────────────────────────
    # from app.api.v1.router import router as v1_router
    # app.include_router(v1_router, prefix="/v1")

    return app


app = create_app()
