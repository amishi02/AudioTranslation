.PHONY: dev-backend dev-frontend lint format test test-backend build-frontend help

# Canonical paths — keep frontend/frontend nested structure documented in phase1.md P1-DEV-001
BACKEND_DIR := backend
FRONTEND_DIR := frontend/frontend

help:
	@echo "Targets:"
	@echo "  dev-backend      - run FastAPI with uvicorn --reload (http://localhost:8000)"
	@echo "  dev-frontend     - run Vite dev server (http://localhost:5173)"
	@echo "  lint             - ruff check + mypy (backend) + eslint (frontend)"
	@echo "  format           - ruff format (backend)"
	@echo "  test             - run all tests (backend pytest)"
	@echo "  test-backend     - pytest -q in backend"
	@echo "  build-frontend   - vite build in frontend"

dev-backend:
	cd $(BACKEND_DIR) && .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd $(FRONTEND_DIR) && npm run dev -- --host

lint:
	cd $(BACKEND_DIR) && .venv/bin/ruff check .
	cd $(BACKEND_DIR) && .venv/bin/mypy app || true
	cd $(FRONTEND_DIR) && npm run lint

format:
	cd $(BACKEND_DIR) && .venv/bin/ruff format .

test: test-backend

test-backend:
	cd $(BACKEND_DIR) && .venv/bin/python -m pytest -q

build-frontend:
	cd $(FRONTEND_DIR) && npm run build
