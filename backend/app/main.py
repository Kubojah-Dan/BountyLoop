"""BountyLoop FastAPI application factory.

Configures CORS, logging, RFC-7807 problem+json error handling,
slowapi rate limiting, health checks, and API v1 routes.
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.router import router as v1_router
from app.core.config import get_settings
from app.core.logging import RequestIdMiddleware, configure_logging
from app.core.metrics import metrics_registry
from app.db.session import get_db
from app.services.security import cv_circuit_breaker

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
    @app.middleware("http")
    async def _metrics_and_latency_middleware(request: Request, call_next: Any) -> Response:
        start_time = time.perf_counter()
        response: Response = await call_next(request)
        duration = time.perf_counter() - start_time
        metrics_registry.record_request(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code,
            duration_seconds=duration,
        )
        return response

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

    # ── Health & Readiness Probes ─────────────────────────────────────────────
    @app.get("/healthz", tags=["ops"], summary="Liveness & Deep Dependency Health Probe")
    async def healthz(
        deep: bool = Query(False, description="Execute deep database and CV checks"),
        db: AsyncSession = Depends(get_db),
    ) -> JSONResponse:
        base_resp: dict[str, Any] = {
            "status": "ok",
            "version": settings.app_version,
            "env": settings.app_env,
        }
        if not deep:
            return JSONResponse(status_code=status.HTTP_200_OK, content=base_resp)

        # Deep health check probing DB, PostGIS, CV service, and circuit breaker
        components: dict[str, Any] = {}
        is_healthy = True

        # 1. PostgreSQL & PostGIS Check
        try:
            t0 = time.perf_counter()
            pg_res = await db.execute(text("SELECT PostGIS_Version();"))
            pg_ver = pg_res.scalar()
            components["database"] = {
                "status": "connected",
                "postgis_version": pg_ver,
                "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
            }
        except Exception as exc:
            is_healthy = False
            components["database"] = {"status": "error", "error": str(exc)}

        # 2. CV Microservice Probe
        try:
            t0 = time.perf_counter()
            async with httpx.AsyncClient(timeout=2.0) as client:
                cv_resp = await client.get(f"{settings.cv_service_url}/healthz")
            if cv_resp.status_code == 200:
                components["cv_service"] = {
                    "status": "online",
                    "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
                    "details": cv_resp.json(),
                }
            else:
                is_healthy = False
                components["cv_service"] = {"status": "degraded", "code": cv_resp.status_code}
        except Exception as exc:
            is_healthy = False
            components["cv_service"] = {"status": "unreachable", "error": str(exc)}

        # 3. Circuit Breaker
        components["circuit_breaker"] = {
            "state": cv_circuit_breaker.state,
            "consecutive_failures": cv_circuit_breaker.consecutive_failures,
        }

        overall_status = "healthy" if is_healthy else "degraded"
        status_code = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

        return JSONResponse(
            status_code=status_code,
            content={
                **base_resp,
                "status": overall_status,
                "components": components,
            },
        )

    # ── Prometheus Metrics ────────────────────────────────────────────────────
    @app.get("/metrics", tags=["ops"], summary="Prometheus format operational metrics")
    async def metrics_endpoint(db: AsyncSession = Depends(get_db)) -> Response:
        """Prometheus metrics exposition endpoint."""
        body = await metrics_registry.generate_prometheus_output(db=db)
        return Response(content=body, media_type="text/plain; version=0.0.4; charset=utf-8")

    # ── API v1 Router ─────────────────────────────────────────────────────────
    app.include_router(v1_router, prefix="/v1")

    return app


app = create_app()
