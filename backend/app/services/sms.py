"""BountyLoop — Twilio SMS Service with Hard Daily Cap.

Provides SMS notification dispatch with hard daily budget enforcement (SMS_DAILY_CAP = 20),
real-time usage auditing, and graceful offline/mock fallback for test and CI environments (§6 Phase 9).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, time
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models.sms_message import SmsMessage

logger = logging.getLogger(__name__)

# Test/in-memory dispatch log for verifying assertions in tests
DISPATCHED_SMS: list[dict[str, Any]] = []


@dataclass
class SmsSendResult:
    """Result of an SMS dispatch attempt."""

    success: bool
    status: str  # "sent", "delivered", "failed", "capped", "mock_sent"
    to_phone: str
    body: str
    daily_count: int
    daily_cap: int
    message_sid: str | None = None
    error: str | None = None


@dataclass
class SmsUsage:
    """Current day's SMS dispatch volume and budget limits."""

    date: str
    sent_today: int
    daily_cap: int
    remaining: int
    is_capped: bool


class TwilioSmsClient:
    """Twilio REST client wrapper enforcing SMS_DAILY_CAP and audit logging."""

    def __init__(
        self,
        account_sid: str | None = None,
        auth_token: str | None = None,
        from_number: str | None = None,
        daily_cap: int | None = None,
    ) -> None:
        settings = get_settings()
        self.account_sid = account_sid if account_sid is not None else settings.twilio_account_sid
        self.auth_token = auth_token if auth_token is not None else settings.twilio_auth_token
        self.from_number = from_number if from_number is not None else settings.twilio_from_number
        self.daily_cap = daily_cap if daily_cap is not None else settings.sms_daily_cap
        self._daily_counts: dict[str, int] = {}

    @property
    def is_configured(self) -> bool:
        """Check if production Twilio credentials are validly provided."""
        return bool(
            self.account_sid
            and self.auth_token
            and self.from_number
            and not self.account_sid.startswith("your-")
            and not self.auth_token.startswith("your-")
        )

    def _get_today_str(self) -> str:
        """Current UTC date formatted as YYYY-MM-DD."""
        return datetime.now(UTC).strftime("%Y-%m-%d")

    async def get_daily_usage(self, db: AsyncSession | None = None) -> SmsUsage:
        """Return the current day's SMS dispatch count, cap, and remaining quota."""
        today_str = self._get_today_str()
        db_count = 0

        if db is not None:
            # Query count of successful/sent outbound SMS since midnight UTC today
            today_midnight = datetime.combine(datetime.now(UTC).date(), time.min, tzinfo=UTC)
            stmt = select(func.count(SmsMessage.id)).where(
                SmsMessage.direction == "outbound",
                SmsMessage.status.in_(["sent", "delivered", "mock_sent"]),
                SmsMessage.created_at >= today_midnight,
            )
            res = await db.execute(stmt)
            db_count = res.scalar_one() or 0

        # Sync in-memory and db counts
        current_in_memory = self._daily_counts.get(today_str, 0)
        sent_today = max(db_count, current_in_memory)
        self._daily_counts[today_str] = sent_today

        remaining = max(0, self.daily_cap - sent_today)
        return SmsUsage(
            date=today_str,
            sent_today=sent_today,
            daily_cap=self.daily_cap,
            remaining=remaining,
            is_capped=sent_today >= self.daily_cap,
        )

    def reset_daily_count_for_test(self, date_str: str | None = None) -> None:
        """Reset test counts to ensure deterministic test runs."""
        target = date_str or self._get_today_str()
        self._daily_counts[target] = 0

    async def send_sms(
        self,
        to_phone: str,
        body: str,
        user_id: uuid.UUID | None = None,
        claim_id: uuid.UUID | None = None,
        db: AsyncSession | None = None,
    ) -> SmsSendResult:
        """Dispatch an SMS notification, enforcing SMS_DAILY_CAP and logging audits.

        If daily cap is reached, suppresses dispatch and records a 'capped' event.
        If live Twilio is unconfigured, operates in mock mode with in-memory tracking.
        """
        clean_to = to_phone.strip()
        usage = await self.get_daily_usage(db)

        # 1. Check Hard Daily Cap
        if usage.sent_today >= self.daily_cap:
            logger.warning(
                "Daily SMS cap (%d) reached! Suppressing SMS to %s. Push notifications remain active.",
                self.daily_cap,
                clean_to,
            )
            # Log capped attempt to DB if session provided
            if db is not None:
                msg_record = SmsMessage(
                    id=uuid.uuid4(),
                    direction="outbound",
                    to_phone=clean_to,
                    from_phone=self.from_number or "+10000000000",
                    body=body,
                    status="capped",
                    error_message=f"Daily SMS cap of {self.daily_cap} exceeded",
                    user_id=user_id,
                    claim_id=claim_id,
                )
                db.add(msg_record)
                await db.commit()

            return SmsSendResult(
                success=False,
                status="capped",
                to_phone=clean_to,
                body=body,
                daily_count=usage.sent_today,
                daily_cap=self.daily_cap,
                error=f"Daily SMS cap of {self.daily_cap} reached",
            )

        # 2. Live Twilio API Dispatch
        if self.is_configured:
            api_url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        api_url,
                        data={
                            "To": clean_to,
                            "From": self.from_number,
                            "Body": body,
                        },
                        auth=(self.account_sid, self.auth_token),
                    )

                if resp.status_code in (200, 201):
                    data = resp.json()
                    sid = data.get("sid", f"SM{uuid.uuid4().hex[:32]}")
                    today_str = self._get_today_str()
                    self._daily_counts[today_str] = self._daily_counts.get(today_str, 0) + 1
                    new_count = self._daily_counts[today_str]

                    if db is not None:
                        msg_record = SmsMessage(
                            id=uuid.uuid4(),
                            direction="outbound",
                            to_phone=clean_to,
                            from_phone=self.from_number,
                            body=body,
                            status="sent",
                            sid=sid,
                            user_id=user_id,
                            claim_id=claim_id,
                        )
                        db.add(msg_record)
                        await db.commit()

                    logger.info(
                        "Twilio SMS sent to %s (SID: %s, daily: %d/%d)",
                        clean_to,
                        sid,
                        new_count,
                        self.daily_cap,
                    )
                    return SmsSendResult(
                        success=True,
                        status="sent",
                        to_phone=clean_to,
                        body=body,
                        daily_count=new_count,
                        daily_cap=self.daily_cap,
                        message_sid=sid,
                    )
                else:
                    error_text = f"Twilio API error {resp.status_code}: {resp.text}"
                    logger.error("Twilio dispatch failed: %s", error_text)
                    if db is not None:
                        msg_record = SmsMessage(
                            id=uuid.uuid4(),
                            direction="outbound",
                            to_phone=clean_to,
                            from_phone=self.from_number,
                            body=body,
                            status="failed",
                            error_message=error_text,
                            user_id=user_id,
                            claim_id=claim_id,
                        )
                        db.add(msg_record)
                        await db.commit()

                    return SmsSendResult(
                        success=False,
                        status="failed",
                        to_phone=clean_to,
                        body=body,
                        daily_count=usage.sent_today,
                        daily_cap=self.daily_cap,
                        error=error_text,
                    )
            except Exception as exc:
                error_text = f"Twilio HTTP exception: {exc}"
                logger.error(error_text)
                if db is not None:
                    msg_record = SmsMessage(
                        id=uuid.uuid4(),
                        direction="outbound",
                        to_phone=clean_to,
                        from_phone=self.from_number or "+10000000000",
                        body=body,
                        status="failed",
                        error_message=error_text,
                        user_id=user_id,
                        claim_id=claim_id,
                    )
                    db.add(msg_record)
                    await db.commit()

                return SmsSendResult(
                    success=False,
                    status="failed",
                    to_phone=clean_to,
                    body=body,
                    daily_count=usage.sent_today,
                    daily_cap=self.daily_cap,
                    error=error_text,
                )

        # 3. Mock / Local Development Mode
        mock_sid = f"SMmock_{uuid.uuid4().hex[:24]}"
        today_str = self._get_today_str()
        self._daily_counts[today_str] = self._daily_counts.get(today_str, 0) + 1
        new_count = self._daily_counts[today_str]

        record = {
            "to": clean_to,
            "from": self.from_number or "+10000000000",
            "body": body,
            "sid": mock_sid,
            "status": "mock_sent",
            "timestamp": datetime.now(UTC).isoformat(),
            "daily_count": new_count,
        }
        DISPATCHED_SMS.append(record)

        if db is not None:
            msg_record = SmsMessage(
                id=uuid.uuid4(),
                direction="outbound",
                to_phone=clean_to,
                from_phone=self.from_number or "+10000000000",
                body=body,
                status="mock_sent",
                sid=mock_sid,
                user_id=user_id,
                claim_id=claim_id,
            )
            db.add(msg_record)
            await db.commit()

        logger.info(
            "Mock SMS dispatched to %s (SID: %s, daily: %d/%d)",
            clean_to,
            mock_sid,
            new_count,
            self.daily_cap,
        )
        return SmsSendResult(
            success=True,
            status="mock_sent",
            to_phone=clean_to,
            body=body,
            daily_count=new_count,
            daily_cap=self.daily_cap,
            message_sid=mock_sid,
        )


twilio_sms_client = TwilioSmsClient()
