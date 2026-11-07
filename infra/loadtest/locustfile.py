"""BountyLoop — Locust Load Sanity Check Script (Phase 12).

Simulates:
- 50 concurrent food donors uploading photos, verifying AI classification, and confirming donations.
- 200 concurrent dashboard & recipient users polling /v1/offers, /v1/impact/summary, and /healthz.

Run headless via:
    locust -f infra/loadtest/locustfile.py --headless -u 250 -r 25 --run-time 1m --host http://localhost:8000
"""

from __future__ import annotations

import io
import random
import uuid

from locust import HttpUser, between, task
from PIL import Image

# Generate a small valid JPEG fixture in-memory
_img_buf = io.BytesIO()
Image.new("RGB", (320, 240), color=(180, 100, 40)).save(_img_buf, format="JPEG")
SAMPLE_JPEG_BYTES = _img_buf.getvalue()


class DonorUser(HttpUser):
    """Simulates active food donors submitting batches and confirming them."""

    weight = 1  # 1 : 4 ratio (50 donors : 200 dashboard pollers)
    wait_time = between(1.5, 4.0)

    def on_start(self) -> None:
        self.donor_uid = f"fb_donor_load_{uuid.uuid4().hex[:8]}"
        self.headers = {"Authorization": f"Bearer mock_token_{self.donor_uid}"}

    @task(3)
    def submit_and_confirm_donation(self) -> None:
        """Create a new donation with multipart photo and confirm it."""
        files = {
            "files": (
                "produce.jpg",
                io.BytesIO(SAMPLE_JPEG_BYTES),
                "image/jpeg",
            )
        }
        data = {
            "est_weight_kg": str(round(random.uniform(2.0, 35.0), 1)),
            "address": "400 E 5th St, Austin, TX",
            "idempotency_key": f"load_{uuid.uuid4()}",
        }

        # 1. Post photo to create donation
        with self.client.post(
            "/v1/donations",
            headers=self.headers,
            files=files,
            data=data,
            catch_response=True,
            name="/v1/donations [create]",
        ) as resp:
            if resp.status_code in (200, 201):
                don_id = resp.json().get("id")
                resp.success()
            else:
                resp.failure(f"Donation create failed with status {resp.status_code}: {resp.text}")
                return

        # 2. Confirm the donation
        if don_id:
            with self.client.patch(
                f"/v1/donations/{don_id}/confirm",
                headers=self.headers,
                json={"item": "produce_fruit", "freshness": "grade_2_good"},
                catch_response=True,
                name="/v1/donations/:id/confirm",
            ) as confirm_resp:
                if confirm_resp.status_code == 200:
                    confirm_resp.success()
                else:
                    confirm_resp.failure(f"Confirm failed with status {confirm_resp.status_code}")


class DashboardAndRecipientUser(HttpUser):
    """Simulates high-frequency dashboard monitoring and recipient offer discovery."""

    weight = 4  # 4x volume representing community pollers
    wait_time = between(0.5, 2.0)

    def on_start(self) -> None:
        self.recip_uid = f"fb_recip_load_{uuid.uuid4().hex[:8]}"
        self.headers = {"Authorization": f"Bearer mock_token_{self.recip_uid}"}

    @task(5)
    def poll_available_offers(self) -> None:
        """Poll nearby surplus offers within 25km radius."""
        self.client.get(
            "/v1/offers?radius_km=25.0&limit=30",
            headers=self.headers,
            name="/v1/offers [poll]",
        )

    @task(3)
    def poll_impact_summary(self) -> None:
        """Fetch real-time impact aggregation metrics."""
        self.client.get(
            "/v1/impact/summary",
            name="/v1/impact/summary",
        )

    @task(2)
    def check_deep_health(self) -> None:
        """Deep health probe query."""
        self.client.get(
            "/healthz?deep=true",
            name="/healthz?deep=true",
        )

    @task(1)
    def scrape_metrics(self) -> None:
        """Scrape Prometheus metrics."""
        self.client.get(
            "/metrics",
            name="/metrics",
        )

