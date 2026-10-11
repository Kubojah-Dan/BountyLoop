# BountyLoop Makefile
# Usage: make <target>
# Requires: Docker Compose, Python 3.12 in .venv, Node 22

SHELL := /bin/bash
.DEFAULT_GOAL := help
PYTHON := .venv/Scripts/python
PIP := .venv/Scripts/pip

# ─── Help ─────────────────────────────────────────────────────────────────────
.PHONY: help
help:
	@echo ""
	@echo "  BountyLoop — Makefile targets"
	@echo "  ────────────────────────────────────────────────────"
	@echo "  Environment"
	@echo "    venv          Create .venv and install backend deps"
	@echo "    install-ml    Install ML deps into .venv"
	@echo "  Docker"
	@echo "    up            docker compose up --build (detached)"
	@echo "    down          docker compose down"
	@echo "    logs          Follow logs for all services"
	@echo "    ps            Show running services"
	@echo "  Database"
	@echo "    migrate       alembic upgrade head"
	@echo "    downgrade     alembic downgrade -1"
	@echo "    seed          Run seed.py (idempotent)"
	@echo "  Quality"
	@echo "    fmt           Run black + ruff --fix"
	@echo "    lint          Run ruff + mypy"
	@echo "    test          Run pytest (backend)"
	@echo "    test-cv       Run pytest (cv_service)"
	@echo "  Health checks"
	@echo "    health        curl both /healthz endpoints"
	@echo "    smoke         POST a synthetic transaction (Phase 13)"
	@echo "  ────────────────────────────────────────────────────"
	@echo ""

# ─── Environment ──────────────────────────────────────────────────────────────
.PHONY: venv
venv:
	python -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -e backend/[dev]

.PHONY: install-ml
install-ml:
	$(PIP) install -r ml/requirements-ml.txt

# ─── Docker ───────────────────────────────────────────────────────────────────
.PHONY: up
up:
	docker compose up --build -d

.PHONY: down
down:
	docker compose down

.PHONY: logs
logs:
	docker compose logs -f

.PHONY: ps
ps:
	docker compose ps

# ─── Database ─────────────────────────────────────────────────────────────────
.PHONY: migrate
migrate:
	docker compose exec api alembic upgrade head

.PHONY: downgrade
downgrade:
	docker compose exec api alembic downgrade -1

.PHONY: seed
seed:
	docker compose exec api python scripts/seed.py

# ─── Quality ──────────────────────────────────────────────────────────────────
.PHONY: fmt
fmt:
	$(PYTHON) -m black backend/ cv_service/ mcp_servers/ ml/src/
	$(PYTHON) -m ruff check --fix backend/ cv_service/ mcp_servers/ ml/src/

.PHONY: lint
lint:
	$(PYTHON) -m ruff check backend/ cv_service/ mcp_servers/ ml/src/
	$(PYTHON) -m mypy backend/app/ cv_service/app/

.PHONY: test
test:
	$(PYTHON) -m pytest backend/tests/ -v --tb=short

.PHONY: test-cv
test-cv:
	$(PYTHON) -m pytest cv_service/tests/ -v --tb=short

# ─── Health / smoke ───────────────────────────────────────────────────────────
.PHONY: health
health:
	@echo "→ API health:"
	@curl -s http://localhost:8000/healthz | python -m json.tool || echo "API not running"
	@echo "→ CV health:"
	@curl -s http://localhost:8001/healthz | python -m json.tool || echo "CV not running"

.PHONY: smoke
smoke:
	@echo "→ Running smoke test (Phase 13)..."
	@$(PYTHON) infra/loadtest/smoke.py
