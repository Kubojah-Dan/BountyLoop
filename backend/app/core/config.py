"""BountyLoop API — core configuration via pydantic-settings.

All variables are read from the environment (or .env file in development).
No secrets are committed or hardcoded.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────────────
    app_env: Literal["development", "staging", "production"] = "development"
    app_version: str = "0.1.0"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # ── API server ────────────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    # Stored as a plain str so pydantic-settings v2 does not try to JSON-decode
    # a comma-separated value. Use the cors_origins_list property everywhere.
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        """Return CORS_ORIGINS as a list, split on commas."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://bountyloop:changeme@db:5432/bountyloop"
    database_url_sync: str = "postgresql+psycopg://bountyloop:changeme@db:5432/bountyloop"

    # ── CV service ────────────────────────────────────────────────────────────
    cv_service_url: str = "http://cv:8001"
    cv_timeout_seconds: float = 10.0
    cv_max_retries: int = 1

    # ── Firebase Auth ─────────────────────────────────────────────────────────
    firebase_project_id: str = ""
    firebase_client_email: str = ""
    firebase_private_key: str = ""  # newline-escaped in env var

    # ── Rate limiting ─────────────────────────────────────────────────────────
    rate_limit_per_minute: int = 60

    # ── CV confidence thresholds ──────────────────────────────────────────────
    auto_conf: float = 0.90
    confirm_conf: float = 0.60
    hazard_forces_review: bool = True
    max_upload_mb: int = 10
    tta: bool = True

    # ── Impact calculation ────────────────────────────────────────────────────
    meal_kg_factor: float = 1.2  # kg per meal equivalent
    impact_co2e_factor: float = 2.5  # kg CO2e per kg food waste avoided [UNVERIFIED]

    # ── Matching engine ───────────────────────────────────────────────────────
    max_radius_km: float = 15.0
    max_consecutive_wins: int = 3
    offer_ttl_minutes: int = 30

    # ── Agent ─────────────────────────────────────────────────────────────────
    agent_enabled: bool = False
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_api_key: str = ""
    agent_max_calls_per_day: int = 500

    # ── MCP servers ───────────────────────────────────────────────────────────
    mcp_transport: str = "streamable-http"
    mcp_donation_ledger_url: str = "http://localhost:8010"
    mcp_routing_url: str = "http://localhost:8011"
    mcp_notify_url: str = "http://localhost:8012"
    mcp_charity_directory_url: str = "http://localhost:8013"
    internal_service_token: str = "changeme-internal-token"

    # ── Twilio / SMS ──────────────────────────────────────────────────────────
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
    sms_daily_cap: int = 20

    # ── Routing ───────────────────────────────────────────────────────────────
    osrm_url: str = "http://osrm:5000"
    osrm_fallback_to_estimate: bool = True

    # ── Feature flags ─────────────────────────────────────────────────────────
    forecast_prompts_enabled: bool = False

    # ── Observability ─────────────────────────────────────────────────────────
    sentry_dsn: str = ""
    sentry_environment: str = "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def firebase_private_key_decoded(self) -> str:
        """Replace literal \\n with real newlines (common when reading from env)."""
        return self.firebase_private_key.replace("\\n", "\n")


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance. Use as a FastAPI dependency."""
    return Settings()
