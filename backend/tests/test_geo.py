"""BountyLoop — PostGIS Geospatial Tests (Phase 1).

Tests ST_Distance, ST_DWithin, and geospatial spatial filtering using
PostGIS 3.4 geography(Point, 4326) columns and GIST indexes.
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Donor, Recipient


@pytest.mark.anyio
async def test_postgis_st_distance_plausible_meters(db_session: AsyncSession) -> None:
    """Test ST_Distance returns physically plausible meter values between donors and recipients."""
    query = (
        select(
            Donor.address.label("donor_addr"),
            Recipient.address.label("recip_addr"),
            func.ST_Distance(Donor.location, Recipient.location).label("distance_m"),
        )
        .select_from(Donor)
        .join(Recipient, func.ST_DWithin(Donor.location, Recipient.location, 35000.0))
        .limit(5)
    )
    result = await db_session.execute(query)
    rows = result.all()

    assert len(rows) > 0, "Expected seeded donors and recipients within city bounds"
    for row in rows:
        distance = float(row.distance_m)
        # Distances within Austin metro area should be between 500m and 35,000m (0.5km to 35km)
        assert (
            500.0 < distance < 35000.0
        ), f"Distance {distance}m between {row.donor_addr} and {row.recip_addr} is out of expected city range"


@pytest.mark.anyio
async def test_postgis_st_dwithin_radius_filter(db_session: AsyncSession) -> None:
    """Test ST_DWithin filters recipients within rescue radiuses."""
    donor_res = await db_session.execute(select(Donor).limit(1))
    donor = donor_res.scalar_one()

    # Find recipients within 10,000 meters (10 km)
    query_10k = select(Recipient).where(
        func.ST_DWithin(Recipient.location, donor.location, 10000.0)
    )
    recipients_within_10k = (await db_session.execute(query_10k)).scalars().all()

    # Find recipients within 25,000 meters (25 km)
    query_25k = select(Recipient).where(
        func.ST_DWithin(Recipient.location, donor.location, 25000.0)
    )
    recipients_within_25k = (await db_session.execute(query_25k)).scalars().all()

    assert len(recipients_within_10k) > 0, "Expected at least one recipient within 10km"
    assert len(recipients_within_25k) >= len(
        recipients_within_10k
    ), "Larger radius must include equal or more recipients"


@pytest.mark.anyio
async def test_postgis_raw_query(db_session: AsyncSession) -> None:
    """Test raw PostGIS ST_Distance query directly matching acceptance criterion."""
    query = text("SELECT ST_Distance(a.location, b.location) FROM donors a, recipients b LIMIT 1;")
    result = await db_session.execute(query)
    distance_val = result.scalar_one()

    assert distance_val is not None
    assert float(distance_val) > 0.0
    # Plausible city scale: between 500m and 35,000m
    assert 500.0 < float(distance_val) < 35000.0
