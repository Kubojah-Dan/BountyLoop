"""BountyLoop — API v1 Root Router.

Aggregates auth, users, and future resource routers under the /v1 prefix.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes import auth, donations, review_queue, users, ws

router = APIRouter()

router.include_router(auth.router)
router.include_router(users.router)
router.include_router(donations.router)
router.include_router(review_queue.router)
router.include_router(ws.router)
