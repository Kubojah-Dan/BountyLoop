"""BountyLoop — Agent API Schemas (§Master Plan §6 Phase 8).

Defines Pydantic request and response models for:
- POST /v1/agent/run
- POST /v1/agent/evaluate
- GET /v1/agent/events
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AgentRunRequest(BaseModel):
    """Payload to trigger autonomous rescue coordination on a donation."""

    donation_id: uuid.UUID = Field(..., description="ID of open donation to coordinate")
    radius_km: float = Field(default=25.0, ge=0.5, le=100.0, description="Spatial search radius")
    auto_accept_threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Confidence threshold for autonomous auto-acceptance (default: 80.0)",
    )
    dry_run: bool = Field(
        default=False,
        description="Dry-run simulation mode without persisting claims or status changes",
    )


class AgentStepTrace(BaseModel):
    """Single step in the ReAct reasoning trace."""

    step: int
    thought: str
    action: str
    action_input: dict[str, Any] = Field(default_factory=dict)
    observation: str


class AgentRunResponse(BaseModel):
    """Result of an autonomous rescue agent run."""

    donation_id: uuid.UUID
    action_taken: str = Field(
        ...,
        description="One of: auto_matched, offer_proposed, escalated_to_human, no_action",
    )
    claim_id: uuid.UUID | None = None
    recipient_id: uuid.UUID | None = None
    confidence_score: float
    threshold: float | None = None
    trace: list[AgentStepTrace] = Field(default_factory=list)
    event_id: uuid.UUID | None = None
    latency_ms: int
    dry_run: bool = False


class AgentEventRead(BaseModel):
    """Auditable log entry from agent_events table."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    donation_id: uuid.UUID | None = None
    event_type: str
    payload: dict[str, Any]
    model: str
    latency_ms: int
    created_at: datetime
