"""BountyLoop — User and authentication Pydantic schemas.

Models for user profile reading, updating, role onboarding, and session initiation.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.db.models.enums import UserRole


class UserBase(BaseModel):
    """Base fields shared across user schemas."""

    email: EmailStr
    display_name: str = Field(..., min_length=1, max_length=255)
    phone_e164: str | None = Field(default=None, max_length=32)
    org_name: str | None = Field(default=None, max_length=255)


class UserRead(UserBase):
    """Complete user profile representation returned by API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    firebase_uid: str
    role: UserRole
    is_active: bool
    created_at: datetime
    last_seen_at: datetime


class UserUpdate(BaseModel):
    """Payload for updating user profile fields."""

    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    phone_e164: str | None = Field(default=None, max_length=32)
    org_name: str | None = Field(default=None, max_length=255)


class RoleUpdateRequest(BaseModel):
    """Payload for setting or switching a user's role during onboarding."""

    role: UserRole = Field(description="Selected user role (donor, recipient, volunteer)")
    org_name: str | None = Field(
        default=None, max_length=255, description="Organization name if applicable"
    )


class SessionCreate(BaseModel):
    """Payload to initiate a session with a Firebase ID token."""

    id_token: str = Field(..., min_length=10, description="Firebase Auth JWT ID token")


class SessionResponse(BaseModel):
    """Response returned upon successful authentication/session creation."""

    user_id: uuid.UUID
    role: UserRole
    profile: UserRead
