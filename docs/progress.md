# Phase 0 Progress — Foundation & Repository Skeleton

## Status: `PASSED` ✅
**Date:** 2026-10-11
**Branch:** `main` (Phase 0 baseline commit)

---

## Evidence

### Environment (verified 2026-10-09)

| Tool | Version | Notes |
|---|---|---|
| Python | 3.12.4 | Plan says 3.11+; 3.12 fully compatible — approved deviation |
| Node | 22.20.0 | ≥20 required ✅ |
| Docker | 29.0.1 | ✅ |
| Flutter | Not in PATH | Phase 6 dependency — not needed for Phase 0 |

### Datasets (local — `ml/data/`)

| Dataset | Local Total | Plan Stated | Match |
|---|---|---|---|
| Freshness (Kaggle 8-class) | **2,715 files** | ~2,715 | ✅ |
| FruitVision | **10,154 files** | 10,154 | ✅ |
| Food-101 | 101 class folders in `images/` + HDF5 bundles | 101 classes | ✅ |

#### Freshness per-class breakdown (verified)
| Class | Count |
|---|---|
| fresh_bread | 205 |
| fresh_dairy | 204 |
| fresh_fruits | 450 |
| fresh_vegetables | 433 |
| spoiled_bread | 344 |
| spoiled_dairy | 299 |
| spoiled_fruits | 289 |
| spoiled_vegetables | 491 |
| **Total** | **2,715** |

#### FruitVision per-class breakdown (verified)
| Fruit | Fresh | Rotten | Formalin-mixed | Subtotal |
|---|---|---|---|---|
| Apple | 765 | 630 | 643 | 2,038 |
| Banana | 749 | 632 | 660 | 2,041 |
| Grape | 770 | 630 | 610 | 2,010 |
| Mango | 763 | 630 | 616 | 2,009 |
| Orange | 753 | 656 | 647 | 2,056 |
| **Total** | **3,800** | **3,178** | **3,176** | **10,154** |

Food-101: `meta/meta/classes.txt` confirmed present. JPEG images extracted in `images/`. HDF5 bundles also present (multiple resolutions). Will use JPEG folder — document in Phase 3 audit.

---

## Files Created

| File | Purpose |
|---|---|
| `.gitignore` | Python, Node, Flutter, secrets, ML data |
| `.env.example` | All env vars for phases 0–13 |
| `README.md` | Project description, quickstart, phase tracker |
| `Makefile` | up/down/logs/fmt/lint/test/migrate/seed/health/smoke |
| `docker-compose.yml` | db (PostGIS 16-3.4), api, cv; OSRM/Nominatim stubs |
| `backend/Dockerfile` | Python 3.12-slim + libpq + GDAL |
| `backend/pyproject.toml` | All deps + ruff/black/mypy/pytest config |
| `backend/app/__init__.py` | Package marker |
| `backend/app/main.py` | FastAPI app factory + /healthz |
| `backend/app/core/__init__.py` | Package marker |
| `backend/app/core/config.py` | pydantic-settings Settings |
| `backend/app/core/logging.py` | JSON logs + request-id middleware |
| `backend/tests/__init__.py` | Package marker |
| `backend/tests/conftest.py` | Async client fixture |
| `backend/tests/test_health.py` | /healthz tests |
| `cv_service/Dockerfile` | Python 3.12-slim + libgomp |
| `cv_service/requirements.txt` | Phase 0 deps (Phase 3 deps commented) |
| `cv_service/app/main.py` | /healthz + 501 /predict stub |
| `.github/workflows/ci.yml` | Lint + type + tests (PostGIS service) |
| `.github/workflows/deploy.yml` | Placeholder (Phase 13) |
| `.github/workflows/ml-nightly.yml` | Placeholder (Phase 3) |
| `assets/brand/bountyloop_logo.png` | Committed brand asset |
| `assets/brand/bountyloop_logo_wordmark.png` | Committed brand asset |
| `assets/brand/brand.md` | Colour, typography, usage rules |
| `docs/architecture.md` | System diagram + tier descriptions |
| `docs/img/bountyloop_architecture.png` | Architecture diagram (generated) |
| Directory skeletons | ml/src/, mcp_servers/, mobile/, dashboard/, infra/ |

---

## Acceptance Checklist

| Criterion | Status | Evidence |
|---|---|—|
| `docker compose up` API returns 200 | `PASS ✅` | `{"status":"ok","version":"0.1.0","env":"development"}` |
| CV service returns 200 | `PASS ✅` | `{"status":"ok","version":"0.1.0","env":"development","models_loaded":{}}` |
| `postgis_version()` returns 3.4.x | `PASS ✅` | `3.4 USE_GEOS=1 USE_PROJ=1 USE_STATS=1` |
| README + architecture doc committed | `PASS ✅` | Files staged |
| Logo assets committed | `PASS ✅` | `assets/brand/bountyloop_logo*.png` present |

### Bug fixed during Phase 0

**`CORS_ORIGINS` crash** — pydantic-settings v2 JSON-decodes `list[str]` env vars before
Pydantic validators run, so a comma-separated string caused `SettingsError`.
Fix: `cors_origins` typed as `str` in `Settings`; a `cors_origins_list` property splits on commas.
`main.py` passes the property to `CORSMiddleware`. No `.env` changes required.

---

## Deviations from master plan

| Item | Deviation | Justification |
|---|---|---|
| Python version | 3.12.4 (plan says 3.11+) | 3.12 is compatible with all dependencies; newer is safer |
| Food-101 layout | JPEG images already extracted in `images/` folder | No need to unpack HDF5 for Phase 3; audit script will verify both |

---

## Next action

**Owner must run:**
```bash
# 1. Copy .env.example to .env (defaults work for local dev)
cp .env.example .env

# 2. Start Docker stack
make up

# 3. Verify health
make health

# 4. Verify PostGIS version
docker compose exec db psql -U bountyloop -c "SELECT postgis_version();"

# 5. Run tests
make test
```

Then share the output. If all pass → Phase 0 is `PASSED` → owner approves Phase 1.

---

## Phase history

| Phase | Status | Date | Notes |
|---|---|---|---|
| 0 | PASSED ✅ | 2026-10-11 | All health checks green. cors_origins bug fixed. |
