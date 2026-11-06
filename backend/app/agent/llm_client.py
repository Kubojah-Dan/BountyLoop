"""BountyLoop — LLM Client Interface for Autonomous Rescue Agent.

Provides structured ReAct generation using Anthropic Claude 3.5 Sonnet, OpenAI,
or deterministic offline execution (§Master Plan §6 Phase 8).
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import httpx

from app.agent.prompt import SYSTEM_PROMPT
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Pluggable client supporting live LLM APIs and deterministic local execution."""

    def __init__(self) -> None:
        settings = get_settings()
        self.provider = os.getenv("LLM_PROVIDER", settings.llm_provider).lower()
        self.model = os.getenv("LLM_MODEL", settings.llm_model)
        self.api_key = os.getenv("LLM_API_KEY", settings.llm_api_key)
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

    @property
    def is_live(self) -> bool:
        """True if an external LLM API key is actively configured."""
        return bool(self.api_key or self.anthropic_key)

    async def generate_react_step(
        self,
        context: str,
        history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Generate one step in the ReAct loop: thought, action, and input."""
        start_time = time.perf_counter()

        # 1. Anthropic Claude 3.5 Sonnet API
        if (self.provider == "anthropic" or self.anthropic_key) and (
            self.anthropic_key or self.api_key
        ):
            key = self.anthropic_key or self.api_key
            try:
                headers = {
                    "x-api-key": key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                }
                messages = [{"role": "user", "content": context}]
                if history:
                    messages = history + messages

                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        "https://api.anthropic.com/v1/messages",
                        headers=headers,
                        json={
                            "model": self.model
                            if "claude" in self.model
                            else "claude-3-5-sonnet-20241022",
                            "system": SYSTEM_PROMPT,
                            "messages": messages,
                            "max_tokens": 1024,
                            "temperature": 0.1,
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        text = data["content"][0]["text"]
                        elapsed = int((time.perf_counter() - start_time) * 1000)
                        return {
                            "text": text,
                            "model": "claude-3-5-sonnet",
                            "latency_ms": elapsed,
                            "mode": "live",
                        }
            except Exception as e:
                logger.warning("Anthropic API call failed (%s); using deterministic runner", e)

        # 2. OpenAI GPT-4o / GPT-4o-mini API
        if self.provider == "openai" and self.api_key:
            try:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": context},
                ]
                if history:
                    messages.extend(history)

                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers=headers,
                        json={
                            "model": self.model,
                            "messages": messages,
                            "max_tokens": 1024,
                            "temperature": 0.1,
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        text = data["choices"][0]["message"]["content"]
                        elapsed = int((time.perf_counter() - start_time) * 1000)
                        return {
                            "text": text,
                            "model": self.model,
                            "latency_ms": elapsed,
                            "mode": "live",
                        }
            except Exception as e:
                logger.warning("OpenAI API call failed (%s); using deterministic runner", e)

        # 3. Deterministic Local Engine (Self-contained, reproducible, safe for testing & CI)
        elapsed = int((time.perf_counter() - start_time) * 1000)
        return {
            "text": "Deterministic ReAct engine active.",
            "model": "bountyloop-react-coordinator",
            "latency_ms": max(1, elapsed),
            "mode": "deterministic",
        }


llm_client = LLMClient()
