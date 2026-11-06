"""BountyLoop — Routing and Polyline Service.

Provides driving route geometries, distances, and ETAs via local or public OSRM,
with a transparent, honestly labeled straight-line estimate fallback (§Master Plan §6 Phase 7).
"""

from __future__ import annotations

import logging
import math
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Configurable OSRM backend endpoint
OSRM_BASE_URL = os.environ.get("OSRM_BASE_URL", "").rstrip("/")
CITY_AVERAGE_SPEED_MPS = 11.11  # 40 km/h average urban rescue transit speed


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate Great Circle distance between two points in meters."""
    r = 6371000.0  # Earth's radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def generate_estimate_route(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> dict[str, Any]:
    """Generate an honest straight-line road estimate with interpolated GeoJSON coordinates."""
    distance_m = haversine_distance_meters(lat1, lon1, lat2, lon2)
    # Estimate road distance factor ~1.25x of straight line in city grid
    road_distance_m = round(distance_m * 1.25, 1)
    duration_s = round(road_distance_m / CITY_AVERAGE_SPEED_MPS, 1)

    # 5-point interpolated GeoJSON LineString
    coords: list[list[float]] = []
    num_steps = 5
    for i in range(num_steps + 1):
        frac = i / float(num_steps)
        lat = lat1 + (lat2 - lat1) * frac
        lon = lon1 + (lon2 - lon1) * frac
        coords.append([round(lon, 6), round(lat, 6)])

    return {
        "geometry": {
            "type": "LineString",
            "coordinates": coords,
        },
        "distance_m": road_distance_m,
        "duration_s": duration_s,
        "source": "estimate",
    }


async def get_route(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> dict[str, Any]:
    """Retrieve driving route geometry and duration.

    Queries OSRM if configured; otherwise gracefully returns an honest estimate.
    """
    if OSRM_BASE_URL:
        try:
            url = f"{OSRM_BASE_URL}/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    routes = data.get("routes", [])
                    if routes:
                        primary = routes[0]
                        return {
                            "geometry": primary.get("geometry"),
                            "distance_m": float(primary.get("distance", 0.0)),
                            "duration_s": float(primary.get("duration", 0.0)),
                            "source": "osrm",
                        }
        except Exception as err:
            logger.info("OSRM request failed (%s); falling back to honest estimate", err)

    return generate_estimate_route(lat1, lon1, lat2, lon2)
