# OSRM Self-Hosted Routing — Setup Guide

> **Phase 7 — add OSRM when matching engine is built.**

## Overview

BountyLoop uses OSRM (Open Source Routing Machine) for car-routing within the pilot city.
Data comes from [Geofabrik](https://download.geofabrik.de/) — free and open source.

## Decision log

When setting up routing for the pilot city, choose one of:

1. **Self-hosted OSRM** (always-on container) — accurate, but costs ~$5–7/month on a small VPS outside Render's free tier. Record the cost decision in `docs/cost-decisions.md`.
2. **OSRM public demo server** (dev only) — free, limited, not for production. Clearly label as `route_source: estimate`.
3. **Straight-line estimate fallback** — always available in code, clearly labeled `route_source: estimate`.

## Setup steps (when ready in Phase 7)

### 1. Download a city OSM extract

```bash
# Example: download a city from Geofabrik
# Replace 'india/kerala' with your actual pilot city region
wget https://download.geofabrik.de/asia/india/kerala-latest.osm.pbf \
     -O infra/osrm/data/city.osm.pbf
```

### 2. Pre-process the extract

```bash
docker run -t -v $(pwd)/infra/osrm/data:/data \
    osrm/osrm-backend osrm-extract \
    -p /opt/car.lua /data/city.osm.pbf

docker run -t -v $(pwd)/infra/osrm/data:/data \
    osrm/osrm-backend osrm-partition /data/city.osrm

docker run -t -v $(pwd)/infra/osrm/data:/data \
    osrm/osrm-backend osrm-customize /data/city.osrm
```

### 3. Enable in docker-compose.yml

Uncomment the `osrm` service block in `docker-compose.yml`.

### 4. Verify

```bash
curl "http://localhost:5000/route/v1/driving/80.2707,13.0827;80.2785,13.0878"
# Should return a route JSON with legs and distance
```

## Attribution

All map and routing data: © OpenStreetMap contributors.  
Display this attribution on every map in the app and dashboard.

## File sizes (approximate — verify before extracting on limited disk)

| Region | .osm.pbf size | Extracted OSRM size |
|---|---|---|
| Small city | ~50–200 MB | ~200–800 MB |
| State/province | ~500 MB–2 GB | ~2–8 GB |

Check free disk before extraction: `df -h`
