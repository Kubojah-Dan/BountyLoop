"""BountyLoop — Security, Firebase Authentication & Role Guards.

Provides token verification with Firebase Auth, automatic user provisioning on first sight,
and role-based access control (RBAC) dependency factories.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import firebase_admin
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.base import utc_now
from app.db.models import User, UserRole
from app.db.session import get_db

logger = logging.getLogger(__name__)
settings = get_settings()

# HTTP Bearer scheme for Authorization: Bearer <token>
http_bearer = HTTPBearer(auto_error=False)

# Singleton state for Firebase App initialization
_firebase_initialized = False


def init_firebase() -> None:
    """Initialize Firebase Admin SDK with service account or default credentials."""
    global _firebase_initialized
    if _firebase_initialized or len(firebase_admin._apps) > 0:
        _firebase_initialized = True
        return

    if (
        settings.firebase_project_id
        and settings.firebase_client_email
        and settings.firebase_private_key
    ):
        try:
            # Handle newline escaping in private key
            private_key = settings.firebase_private_key.replace("\\n", "\n")
            cred = credentials.Certificate(
                {
                    "type": "service_account",
                    "project_id": settings.firebase_project_id,
                    "client_email": settings.firebase_client_email,
                    "private_key": private_key,
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            )
            firebase_admin.initialize_app(cred)
            _firebase_initialized = True
            logger.info(
                "Firebase Admin SDK initialized with configured service account credentials"
            )
        except Exception as exc:
            logger.warning("Failed to initialize Firebase Admin SDK with service account: %s", exc)
    else:
        logger.info(
            "Firebase credentials not configured in environment — relying on default or mocked credentials"
        )


def verify_firebase_token(id_token: str) -> dict[str, Any]:
    """Verify a Firebase Auth ID token and return decoded claims.

    Raises HTTPException 401 if invalid, expired, or unverified.
    """
    init_firebase()
    try:
        decoded = firebase_auth.verify_id_token(id_token)
        return decoded
    except Exception as exc:
        logger.warning("Firebase token verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or malformed authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_user(
    auth_header: HTTPAuthorizationCredentials | None = Depends(http_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency to extract Bearer token, verify claims, and provision/load User entity."""
    if not auth_header or not auth_header.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials are required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header.credentials
    claims = verify_firebase_token(token)
    firebase_uid = claims.get("uid")

    if not firebase_uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token does not contain a valid user identifier.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Lookup user by firebase_uid
    query = select(User).where(User.firebase_uid == firebase_uid)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if user is None:
        # First sight: provision new user automatically (onboarding state)
        email = claims.get("email") or f"{firebase_uid}@bountyloop.local"
        name = claims.get("name") or email.split("@")[0]

        # Check if email is already registered to avoid unique constraint conflict
        existing_email_user = (
            await db.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
        if existing_email_user is not None:
            existing_email_user.firebase_uid = firebase_uid
            existing_email_user.last_seen_at = utc_now()
            await db.commit()
            return existing_email_user

        user = User(
            firebase_uid=firebase_uid,
            role=UserRole.donor,  # Default role prior to onboarding completion
            display_name=name,
            email=email,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info(
            "Provisioned new user on first sight: id=%s uid=%s email=%s",
            user.id,
            firebase_uid,
            email,
        )
    else:
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated.",
            )
        # Update last_seen_at timestamp
        user.last_seen_at = utc_now()
        await db.commit()

    return user


def require_role(*allowed_roles: UserRole | str) -> Callable[..., Any]:
    """Dependency factory restricting route access to specified roles.

    Returns 401 if unauthenticated, 403 if authenticated with insufficient role.
    """
    normalized_roles = {r.value if isinstance(r, UserRole) else str(r) for r in allowed_roles}

    async def _role_guard(current_user: User = Depends(get_current_user)) -> User:
        user_role_val = (
            current_user.role.value
            if isinstance(current_user.role, UserRole)
            else str(current_user.role)
        )
        if user_role_val not in normalized_roles:
            logger.warning(
                "Access denied for user %s: role '%s' not in permitted roles %s",
                current_user.id,
                user_role_val,
                normalized_roles,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: this endpoint requires one of the following roles: {', '.join(sorted(normalized_roles))}.",
            )
        return current_user

    return _role_guard
