"""BountyLoop FastAPI application factory.

Configures CORS, logging, RFC-7807 problem+json error handling,
slowapi rate limiting, health checks, and API v1 routes.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.v1.router import router as v1_router
from app.core.config import get_settings
from app.core.logging import RequestIdMiddleware, configure_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle management."""
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info(
        "BountyLoop API starting",
        extra={"version": settings.app_version, "env": settings.app_env},
    )
    yield
    logger.info("BountyLoop API shutting down")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application instance."""
    settings = get_settings()

    # Rate limiter (in-memory for MVP)
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[f"{settings.rate_limit_per_minute}/minute"],
    )

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
    app.state.limiter = limiter

    # ── Middleware ─────────────────────────────────────────────────────────────
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── RFC-7807 Problem Details Exception Handlers ────────────────────────────
    @app.exception_handler(HTTPException)
    async def _http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        titles = {
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            409: "Conflict",
            422: "Unprocessable Entity",
            429: "Too Many Requests",
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
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        invalid_params = []
        for err in exc.errors():
            loc = ".".join(str(p) for p in err.get("loc", []))
            invalid_params.append(
                {
                    "name": loc,
                    "reason": err.get("msg", "Validation error"),
                    "type": err.get("type", "value_error"),
                }
            )
        return JSONResponse(
            status_code=422,
            content={
                "type": "about:blank",
                "title": "Unprocessable Entity",
                "status": 422,
                "detail": "Request payload validation failed.",
                "instance": str(request.url),
                "invalid_params": invalid_params,
            },
            media_type="application/problem+json",
        )

    @app.exception_handler(RateLimitExceeded)
    async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={
                "type": "about:blank",
                "title": "Too Many Requests",
                "status": 429,
                "detail": f"Rate limit exceeded: {exc.detail}",
                "instance": str(request.url),
            },
            media_type="application/problem+json",
        )

    @app.exception_handler(Exception)
    async def _unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled server exception", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={
                "type": "about:blank",
                "title": "Internal Server Error",
                "status": 500,
                "detail": "An unexpected error occurred.",
                "instance": str(request.url),
            },
            media_type="application/problem+json",
        )

    # ── Health Check ──────────────────────────────────────────────────────────
    @app.get("/healthz", tags=["ops"], summary="Liveness probe")
    async def healthz() -> dict[str, str]:
        return {
            "status": "ok",
            "version": settings.app_version,
            "env": settings.app_env,
        }

    # ── API v1 Router ─────────────────────────────────────────────────────────
    app.include_router(v1_router, prefix="/v1")

    return app


app = create_app()
