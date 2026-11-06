# BountyLoop OSRM (Open Source Routing Machine) Guide

This directory documents how to provision and run a local OSRM routing container for BountyLoop pilot deployments.

## 1. Quickstart with Texas / Austin OSM Extract

OSRM requires an `.osm.pbf` road network file. For our Austin, Texas pilot:

```bash
mkdir -p data/osrm
cd data/osrm

# 1. Download regional extract from Geofabrik (~250 MB)
curl -O https://download.geofabrik.de/north-america/us/texas-latest.osm.pbf

# 2. Extract road network graph with car profile
docker run -t -v "${PWD}:/data" ghcr.io/project-osrm/osrm-backend osrm-extract -p /opt/car.lua /data/texas-latest.osm.pbf

# 3. Partition and customize for MLD (Multi-Level Dijkstra) routing
docker run -t -v "${PWD}:/data" ghcr.io/project-osrm/osrm-backend osrm-partition /data/texas-latest.osrm
docker run -t -v "${PWD}:/data" ghcr.io/project-osrm/osrm-backend osrm-customize /data/texas-latest.osrm

# 4. Run routing daemon on port 5000
docker run -d --name bountyloop_osrm -p 5000:5000 -v "${PWD}:/data" ghcr.io/project-osrm/osrm-backend osrm-routed --algorithm mld /data/texas-latest.osrm
```

## 2. Expected Resource and File Sizes

| File | Approximate Size | Purpose |
|---|---|---|
| `texas-latest.osm.pbf` | ~250 MB | Raw OpenStreetMap extract |
| `texas-latest.osrm` | ~600 MB | Graph representation |
| `texas-latest.osrm.mldgr` | ~150 MB | Multi-level hierarchy graph |
| RAM required for Austin / Texas | ~1.5 GB | In-memory routing graph |

## 3. Fallback Mechanism

If `OSRM_BASE_URL` is empty or the OSRM container is uncontactable, BountyLoop automatically falls back to an interpolated Great Circle road estimate ($40\text{ km/h}$ average urban speed, $1.25\times$ grid tortuosity factor) and stamps `route_source: "estimate"`.
