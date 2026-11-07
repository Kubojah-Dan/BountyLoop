"""BountyLoop — API v1 Root Router.

Aggregates auth, users, and future resource routers under the /v1 prefix.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes import (
    agent,
    auth,
    claims,
    devices,
    donations,
    forecast,
    impact,
    offers,
    review_queue,
    routes,
    sms,
    users,
    ws,
)

router = APIRouter()

router.include_router(auth.router)
router.include_router(users.router)
router.include_router(donations.router)
router.include_router(review_queue.router)
router.include_router(offers.router)
router.include_router(claims.router)
router.include_router(devices.router)
router.include_router(routes.router)
router.include_router(agent.router)
router.include_router(sms.router)
router.include_router(impact.router)
router.include_router(forecast.router)
router.include_router(ws.router)
