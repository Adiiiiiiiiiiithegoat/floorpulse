# Linux/macOS/CI. On Windows without make, run the commands under each target directly.
.PHONY: dev backend frontend test test-backend test-frontend e2e lint typecheck migrate seed api-types build up

dev:            ## backend on :8000 and frontend on :5173
	$(MAKE) -j2 backend frontend

backend:
	cd backend && uv run uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

migrate:
	cd backend && uv run alembic upgrade head

seed:           ## rebuild the demo organization (drops local dev data)
	cd backend && uv run python -m app.seed --reset

test: test-backend test-frontend

test-backend:
	cd backend && uv run pytest

test-frontend:
	cd frontend && npm test

e2e:
	cd frontend && npx playwright test

lint:
	cd backend && uv run ruff check . && uv run ruff format --check .
	cd frontend && npm run lint

typecheck:
	cd backend && uv run mypy
	cd frontend && npm run typecheck

api-types:      ## regenerate frontend/src/lib/api-types.ts from the FastAPI schema
	cd frontend && npm run gen:api

build:
	cd frontend && npm run build

up:             ## full stack: Postgres + API + web behind Caddy
	docker compose up -d --build
