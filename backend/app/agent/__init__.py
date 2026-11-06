"""BountyLoop — Autonomous Rescue Coordinator Agent (§Master Plan §6 Phase 8).

Implements autonomous food rescue orchestration using ReAct reasoning:
- Candidate search and PostGIS filtering
- Transparent multi-factor scoring
- Regional equity rebalancing
- High-confidence auto-acceptance & human review escalation
- Full audit event logging
"""

from __future__ import annotations

from app.agent.coordinator import AutonomousRescueAgent, rescue_agent

__all__ = ["AutonomousRescueAgent", "rescue_agent"]

