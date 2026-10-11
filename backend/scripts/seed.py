"""BountyLoop — Database Seeding Script.

Seeds pilot city data (Austin, TX) with real coordinates:
- 1 Admin user
- 5 Donors (grocer, bakery, farm, restaurant, supermarket)
- 8 Recipients (food banks, shelters, community fridges, discount buyers)
- Sample donations with claims and impact log

Idempotent: safe to run repeatedly without creating duplicates.
Usage: python scripts/seed.py (or `make seed`)
"""

from __future__ import annotations

import logging
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Ensure /app is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from geoalchemy2.elements import WKTElement
from sqlalchemy import select

from app.db.models import (
    Claim,
    ClaimStatus,
    Donation,
    DonationStatus,
    Donor,
    DonorKind,
    FoodCategory,
    FreshnessGrade,
    HazardFlag,
    ImpactLog,
    Recipient,
    RecipientOrgType,
    User,
    UserRole,
)
from app.db.session import SyncSessionLocal

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("bountyloop.seed")


def seed_data() -> None:
    """Seed the database with pilot city records."""
    session = SyncSessionLocal()
    try:
        now = datetime.now(UTC)

        # ── 1. Admin User ──────────────────────────────────────────────────────
        admin_email = "admin@bountyloop.org"
        existing_admin = session.execute(
            select(User).where(User.email == admin_email)
        ).scalar_one_or_none()

        if not existing_admin:
            admin_user = User(
                id=uuid.uuid4(),
                firebase_uid="firebase_admin_bountyloop_01",
                role=UserRole.admin,
                display_name="BountyLoop Operations Admin",
                email=admin_email,
                phone_e164="+15125550100",
                org_name="BountyLoop Operations",
                is_active=True,
            )
            session.add(admin_user)
            logger.info("Created admin user: %s", admin_email)
        else:
            logger.info("Admin user already exists: %s", admin_email)

        # ── 2. Donors (Austin, TX) ─────────────────────────────────────────────
        donors_data = [
            {
                "email": "manager@centralmarket-north.com",
                "uid": "fb_donor_central_market_north",
                "name": "Central Market North Lamar",
                "org": "Central Market",
                "phone": "+15125550101",
                "kind": DonorKind.grocery,
                "address": "4001 N Lamar Blvd, Austin, TX 78756",
                "lon": -97.7408,
                "lat": 30.3045,
                "timezone": "America/Chicago",
                "schedule": {"daily_surplus_time": "20:00", "avg_weekly_kg": 450},
            },
            {
                "email": "donations@wholefoods-flagship.com",
                "uid": "fb_donor_wholefoods_flagship",
                "name": "Whole Foods Market Lamar Flagship",
                "org": "Whole Foods Market",
                "phone": "+15125550102",
                "kind": DonorKind.grocery,
                "address": "525 N Lamar Blvd, Austin, TX 78703",
                "lon": -97.7533,
                "lat": 30.2707,
                "timezone": "America/Chicago",
                "schedule": {"daily_surplus_time": "21:30", "avg_weekly_kg": 600},
            },
            {
                "email": "bakehouse@easytiger-atx.com",
                "uid": "fb_donor_easytiger_bakery",
                "name": "Easy Tiger Bake Shop East",
                "org": "Easy Tiger",
                "phone": "+15125550103",
                "kind": DonorKind.restaurant,
                "address": "1501 E 7th St, Austin, TX 78702",
                "lon": -97.7275,
                "lat": 30.2635,
                "timezone": "America/Chicago",
                "schedule": {"daily_surplus_time": "18:00", "avg_weekly_kg": 180},
            },
            {
                "email": "harvest@boggycreekfarm.com",
                "uid": "fb_donor_boggycreek_farm",
                "name": "Boggy Creek Urban Farm",
                "org": "Boggy Creek Farm",
                "phone": "+15125550104",
                "kind": DonorKind.farm,
                "address": "3414 Lyons Rd, Austin, TX 78702",
                "lon": -97.7088,
                "lat": 30.2762,
                "timezone": "America/Chicago",
                "schedule": {"harvest_days": ["Wednesday", "Saturday"], "avg_weekly_kg": 250},
            },
            {
                "email": "manager@tacodeli-slamar.com",
                "uid": "fb_donor_tacodeli_slamar",
                "name": "Tacodeli South Lamar",
                "org": "Tacodeli",
                "phone": "+15125550105",
                "kind": DonorKind.restaurant,
                "address": "4200 S Lamar Blvd, Austin, TX 78704",
                "lon": -97.7852,
                "lat": 30.2370,
                "timezone": "America/Chicago",
                "schedule": {"daily_surplus_time": "15:30", "avg_weekly_kg": 95},
            },
        ]

        created_donors: list[Donor] = []
        for d in donors_data:
            existing_user = session.execute(
                select(User).where(User.email == d["email"])
            ).scalar_one_or_none()

            if not existing_user:
                user = User(
                    id=uuid.uuid4(),
                    firebase_uid=d["uid"],
                    role=UserRole.donor,
                    display_name=d["name"],
                    email=d["email"],
                    phone_e164=d["phone"],
                    org_name=d["org"],
                    is_active=True,
                )
                session.add(user)
                session.flush()

                donor = Donor(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    kind=d["kind"],
                    address=d["address"],
                    location=WKTElement(f"POINT({d['lon']} {d['lat']})", srid=4326),
                    timezone=d["timezone"],
                    avg_surplus_schedule=d["schedule"],
                )
                session.add(donor)
                created_donors.append(donor)
                logger.info("Created donor: %s (%s)", d["name"], d["address"])
            else:
                existing_donor = session.execute(
                    select(Donor).where(Donor.user_id == existing_user.id)
                ).scalar_one_or_none()
                if existing_donor:
                    created_donors.append(existing_donor)
                logger.info("Donor already exists: %s", d["name"])

        # ── 3. Recipients (Austin, TX) ─────────────────────────────────────────
        recipients_data = [
            {
                "email": "dispatch@centraltexasfoodbank.org",
                "uid": "fb_recip_ctfb_main",
                "name": "Central Texas Food Bank Warehouse",
                "org": "Central Texas Food Bank",
                "phone": "+15125550201",
                "org_type": RecipientOrgType.food_bank,
                "address": "6500 Metropolis Dr, Austin, TX 78744",
                "lon": -97.7171,
                "lat": 30.2085,
                "capacity": 2500.0,
                "accepted_items": [
                    "produce_fruit",
                    "produce_vegetable",
                    "bread_bakery",
                    "dairy",
                    "grains_staples",
                    "prepared_cooked",
                ],
                "cold_chain": True,
                "urgency": 1.2,
                "hours": {"mon_fri": "08:00-18:00", "sat": "09:00-14:00"},
            },
            {
                "email": "intake@casamarianella.org",
                "uid": "fb_recip_casa_marianella",
                "name": "Casa Marianella Emergency Shelter",
                "org": "Casa Marianella",
                "phone": "+15125550202",
                "org_type": RecipientOrgType.shelter,
                "address": "821 Gault St, Austin, TX 78702",
                "lon": -97.7011,
                "lat": 30.2755,
                "capacity": 350.0,
                "accepted_items": [
                    "prepared_cooked",
                    "bread_bakery",
                    "dairy",
                    "produce_fruit",
                    "produce_vegetable",
                ],
                "cold_chain": True,
                "urgency": 1.5,
                "hours": {"daily": "07:00-21:00"},
            },
            {
                "email": "pantry@foundcom.org",
                "uid": "fb_recip_foundcom_south",
                "name": "Foundation Communities South First Pantry",
                "org": "Foundation Communities",
                "phone": "+15125550203",
                "org_type": RecipientOrgType.food_bank,
                "address": "3036 S 1st St, Austin, TX 78704",
                "lon": -97.7668,
                "lat": 30.2345,
                "capacity": 600.0,
                "accepted_items": [
                    "produce_fruit",
                    "produce_vegetable",
                    "bread_bakery",
                    "grains_staples",
                    "dairy",
                ],
                "cold_chain": True,
                "urgency": 1.1,
                "hours": {"mon_sat": "09:00-17:00"},
            },
            {
                "email": "kitchen@caritasofaustin.org",
                "uid": "fb_recip_caritas_downtown",
                "name": "Caritas of Austin Community Kitchen",
                "org": "Caritas of Austin",
                "phone": "+15125550204",
                "org_type": RecipientOrgType.shelter,
                "address": "611 Neches St, Austin, TX 78701",
                "lon": -97.7380,
                "lat": 30.2687,
                "capacity": 450.0,
                "accepted_items": [
                    "prepared_cooked",
                    "meat_fish",
                    "produce_vegetable",
                    "bread_bakery",
                    "soup_stew",
                ],
                "cold_chain": False,
                "urgency": 1.4,
                "hours": {"daily": "08:00-16:00"},
            },
            {
                "email": "coordinator@hopefoodpantryaustin.org",
                "uid": "fb_recip_hope_pantry_north",
                "name": "Hope Food Pantry Trinity",
                "org": "Hope Food Pantry",
                "phone": "+15125550205",
                "org_type": RecipientOrgType.food_bank,
                "address": "4001 Speedway, Austin, TX 78751",
                "lon": -97.7285,
                "lat": 30.3030,
                "capacity": 500.0,
                "accepted_items": [
                    "bread_bakery",
                    "produce_fruit",
                    "produce_vegetable",
                    "dairy",
                    "grains_staples",
                ],
                "cold_chain": True,
                "urgency": 1.0,
                "hours": {"thu_fri": "08:30-13:00"},
            },
            {
                "email": "meals@sunrisenav.org",
                "uid": "fb_recip_sunrise_south",
                "name": "Sunrise Homeless Navigation Hub",
                "org": "Sunrise Navigation Center",
                "phone": "+15125550206",
                "org_type": RecipientOrgType.shelter,
                "address": "4430 Manchaca Rd, Austin, TX 78745",
                "lon": -97.7850,
                "lat": 30.2285,
                "capacity": 400.0,
                "accepted_items": ["prepared_cooked", "beverage", "bread_bakery", "produce_fruit"],
                "cold_chain": False,
                "urgency": 1.3,
                "hours": {"daily": "08:00-14:00"},
            },
            {
                "email": "stewards@atxfreefridge.org",
                "uid": "fb_recip_east_free_fridge",
                "name": "ATX Free Fridge East 12th",
                "org": "ATX Free Fridge",
                "phone": "+15125550207",
                "org_type": RecipientOrgType.community_fridge,
                "address": "1105 E 12th St, Austin, TX 78702",
                "lon": -97.7250,
                "lat": 30.2730,
                "capacity": 120.0,
                "accepted_items": [
                    "produce_fruit",
                    "produce_vegetable",
                    "bread_bakery",
                    "dairy",
                    "beverage",
                ],
                "cold_chain": True,
                "urgency": 1.1,
                "hours": {"24_7": True},
            },
            {
                "email": "purchasing@atxdiscountcoop.org",
                "uid": "fb_recip_discount_coop",
                "name": "East Austin Community Discount Market Co-op",
                "org": "Austin Discount Co-op",
                "phone": "+15125550208",
                "org_type": RecipientOrgType.discount_buyer,
                "address": "2908 E 12th St, Austin, TX 78702",
                "lon": -97.7090,
                "lat": 30.2780,
                "capacity": 800.0,
                "accepted_items": [
                    "produce_fruit",
                    "produce_vegetable",
                    "dairy",
                    "meat_fish",
                    "grains_staples",
                ],
                "cold_chain": True,
                "urgency": 0.9,
                "hours": {"mon_sat": "08:00-20:00"},
            },
        ]

        created_recipients: list[Recipient] = []
        for r in recipients_data:
            existing_user = session.execute(
                select(User).where(User.email == r["email"])
            ).scalar_one_or_none()

            if not existing_user:
                user = User(
                    id=uuid.uuid4(),
                    firebase_uid=r["uid"],
                    role=UserRole.recipient,
                    display_name=r["name"],
                    email=r["email"],
                    phone_e164=r["phone"],
                    org_name=r["org"],
                    is_active=True,
                )
                session.add(user)
                session.flush()

                recipient = Recipient(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    org_type=r["org_type"],
                    address=r["address"],
                    location=WKTElement(f"POINT({r['lon']} {r['lat']})", srid=4326),
                    capacity_kg_per_day=r["capacity"],
                    accepted_items=r["accepted_items"],
                    cold_chain=r["cold_chain"],
                    operating_hours=r["hours"],
                    urgency_weight=r["urgency"],
                    is_accepting=True,
                )
                session.add(recipient)
                created_recipients.append(recipient)
                logger.info("Created recipient: %s (%s)", r["name"], r["org_type"])
            else:
                existing_recipient = session.execute(
                    select(Recipient).where(Recipient.user_id == existing_user.id)
                ).scalar_one_or_none()
                if existing_recipient:
                    created_recipients.append(existing_recipient)
                logger.info("Recipient already exists: %s", r["name"])

        # ── 4. Sample Donations with Claims and Impact ─────────────────────────
        if created_donors and created_recipients:
            donor_easy_tiger = created_donors[2] if len(created_donors) > 2 else created_donors[0]
            donor_central_market = created_donors[0]
            recip_ctfb = created_recipients[0]
            recip_casa = created_recipients[1]

            # Donation 1: Completed rescue (Easy Tiger surplus sourdough bread)
            d1_exists = (
                session.execute(select(Donation).where(Donation.donor_id == donor_easy_tiger.id))
                .scalars()
                .first()
            )

            if not d1_exists:
                d1 = Donation(
                    id=uuid.uuid4(),
                    donor_id=donor_easy_tiger.id,
                    photo_paths=["storage/photos/sample_bread_01.jpg"],
                    item=FoodCategory.bread_bakery,
                    item_confidence=0.9620,
                    freshness=FreshnessGrade.fresh,
                    freshness_confidence=0.9410,
                    hazard_flag=HazardFlag.none,
                    est_weight_kg=35.5,
                    expires_at=now + timedelta(hours=24),
                    status=DonationStatus.completed,
                    needs_review=False,
                    model_versions={
                        "item_model": "food101-b0-v1",
                        "freshness_model": "freshness-b0-v1",
                    },
                )
                session.add(d1)
                session.flush()

                c1 = Claim(
                    id=uuid.uuid4(),
                    donation_id=d1.id,
                    recipient_id=recip_casa.id,
                    status=ClaimStatus.picked_up,
                    score=0.9150,
                    score_breakdown={"distance_km": 2.4, "capacity_fit": 0.95, "urgency": 1.5},
                    offered_at=now - timedelta(hours=3),
                    responded_at=now - timedelta(hours=2, minutes=45),
                    picked_up_at=now - timedelta(hours=1),
                    proof_photo_path="storage/photos/proof_pickup_01.jpg",
                )
                session.add(c1)

                impact1 = ImpactLog(
                    id=uuid.uuid4(),
                    donation_id=d1.id,
                    kg_rescued=35.5,
                    meals_equivalent=round(35.5 * 1.2, 1),
                    co2e_avoided_kg=round(35.5 * 2.5, 1),
                    method_version="v1.0",
                )
                session.add(impact1)
                logger.info("Created sample completed donation + claim + impact for Easy Tiger")

            # Donation 2: Active open donation (Central Market fresh produce)
            d2_exists = (
                session.execute(
                    select(Donation).where(
                        Donation.donor_id == donor_central_market.id,
                        Donation.status == DonationStatus.open,
                    )
                )
                .scalars()
                .first()
            )

            if not d2_exists:
                d2 = Donation(
                    id=uuid.uuid4(),
                    donor_id=donor_central_market.id,
                    photo_paths=["storage/photos/sample_produce_01.jpg"],
                    item=FoodCategory.produce_vegetable,
                    item_confidence=0.9380,
                    freshness=FreshnessGrade.fresh,
                    freshness_confidence=0.9120,
                    hazard_flag=HazardFlag.none,
                    est_weight_kg=78.0,
                    expires_at=now + timedelta(hours=36),
                    status=DonationStatus.open,
                    needs_review=False,
                    model_versions={
                        "item_model": "food101-b0-v1",
                        "freshness_model": "freshness-b0-v1",
                    },
                )
                session.add(d2)
                session.flush()

                c2 = Claim(
                    id=uuid.uuid4(),
                    donation_id=d2.id,
                    recipient_id=recip_ctfb.id,
                    status=ClaimStatus.offered,
                    score=0.8840,
                    score_breakdown={"distance_km": 11.2, "capacity_fit": 0.99, "urgency": 1.2},
                    offered_at=now - timedelta(minutes=15),
                )
                session.add(c2)
                logger.info("Created sample active donation + offer for Central Market")

        session.commit()
        logger.info("Database seeding completed successfully.")

    except Exception as exc:
        session.rollback()
        logger.error("Seeding failed: %s", exc, exc_info=True)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_data()
