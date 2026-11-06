"""BountyLoop — Autonomous Rescue Agent API Endpoints (§Master Plan §6 Phase 8).

Provides:
- POST /v1/agent/run: Execute autonomous rescue coordination loop on open donation
- POST /v1/agent/evaluate: Dry-run simulation of agent reasoning without persisting state changes
- GET /v1/agent/events: Paginated audit log of agent events, tool calls, and model decisions
"""

from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.coordinator import rescue_agent
from app.core.security import get_current_user
from app.db.models import AgentEvent, User
from app.db.session import get_db
from app.schemas.agent import AgentEventRead, AgentRunRequest, AgentRunResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post(
    "/run",
    summary="Execute autonomous food rescue coordination on a donation",
    response_model=AgentRunResponse,
    status_code=status.HTTP_200_OK,
)
async def run_agent(
    payload: AgentRunRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentRunResponse:
    """Trigger the multi-turn ReAct rescue coordinator loop on an open donation."""
    try:
        result = await rescue_agent.run(
            donation_id=payload.donation_id,
            db=db,
            radius_km=payload.radius_km,
            auto_accept_threshold=payload.auto_accept_threshold,
            dry_run=payload.dry_run,
        )
        return AgentRunResponse(**result)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
    except Exception as err:
        logger.exception("Autonomous rescue agent run failed: %s", err)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent coordination failed: {err}",
        ) from err


@router.post(
    "/evaluate",
    summary="Dry-run simulation of agent reasoning without modifying state",
    response_model=AgentRunResponse,
    status_code=status.HTTP_200_OK,
)
async def evaluate_agent(
    payload: AgentRunRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentRunResponse:
    """Simulate ReAct reasoning and candidate matching in read-only dry-run mode."""
    try:
        result = await rescue_agent.run(
            donation_id=payload.donation_id,
            db=db,
            radius_km=payload.radius_km,
            auto_accept_threshold=payload.auto_accept_threshold,
            dry_run=True,
        )
        return AgentRunResponse(**result)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err


@router.get(
    "/events",
    summary="List paginated agent audit events and tool execution traces",
    response_model=list[AgentEventRead],
)
async def list_agent_events(
    donation_id: Annotated[uuid.UUID | None, Query()] = None,
    event_type: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AgentEventRead]:
    """Retrieve audit trail of autonomous agent decisions, tool invocations, and ReAct traces."""
    query = select(AgentEvent).order_by(AgentEvent.created_at.desc())

    if donation_id is not None:
        query = query.where(AgentEvent.donation_id == donation_id)
    if event_type is not None:
        query = query.where(AgentEvent.event_type == event_type)

    query = query.limit(limit).offset(offset)
    results = (await db.execute(query)).scalars().all()
    return [AgentEventRead.model_validate(event) for event in results]

