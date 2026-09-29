# FloorPulse

Shop-floor operations for small and mid-size manufacturers: downtime, production, quality, inventory and maintenance, on a cheap Android phone with a weak connection.

- **Backend:** FastAPI + SQLAlchemy 2 + Alembic (`backend/`). SQLite for dev and tests, Postgres in production.
- **Frontend:** React 18 + TypeScript + Vite PWA (`frontend/`). The operator app is at `/floor`, the manager app at `/app`.
- **Docs:** [plan](docs/PLAN.md), [decisions](docs/DECISIONS.md), [data model](docs/DATA_MODEL.md), [API](docs/API.md).

## Quick start (local)

Requirements: Python 3.11+ with [uv](https://docs.astral.sh/uv/), Node 20+.

```sh
cd backend && uv sync && uv run alembic upgrade head && uv run python -m app.seed
cd ../frontend && npm install
make dev          # or run the two commands below in two terminals
# cd backend && uv run uvicorn app.main:app --reload --port 8000
# cd frontend && npm run dev
```

Open http://localhost:5173. API docs are at http://localhost:8000/docs.

### Demo logins (seeded "Demo Auto Components Pvt Ltd")

| Who | Sign in | Credentials |
|---|---|---|
| Admin | `/login` | `admin@demo.floorpulse.app` / `FloorPulse!2026` |
| Plant manager | `/login` | `manager@demo.floorpulse.app` / `FloorPulse!2026` |
| Supervisors | `/login` | `supervisor.pune@…`, `supervisor.chennai@…` / `FloorPulse!2026` |
| Technician, inspector, store keeper | `/login` | `tech@…`, `quality@…`, `stores@…` / `FloorPulse!2026` |
| Operators (Ganesh, Lakshmi at Pune; Mohan, Kavita at Chennai) | `/floor` | PIN `1234` |

The operator app needs a registered device. Either register one at `/floor/setup` with a supervisor login, or use a seeded demo device by running this once in the browser console:
`localStorage.setItem('fp_device_token', 'demo-device-pun')` (or `demo-device-che`).

## Commands

| Task | Make | Raw command |
|---|---|---|
| Tests | `make test` | `cd backend && uv run pytest`; `cd frontend && npm test` |
| End-to-end | `make e2e` | `cd frontend && npx playwright test` (starts its own servers on a throwaway DB) |
| Lint / types | `make lint typecheck` | `uv run ruff check . && uv run mypy`; `npm run lint && npm run typecheck` |
| Migrate | `make migrate` | `cd backend && uv run alembic upgrade head` |
| Reset demo data | `make seed` | `cd backend && uv run python -m app.seed --reset` |
| Regenerate API types | `make api-types` | `cd frontend && npm run gen:api` |

## Production

`docker compose up -d --build` runs Postgres, the API and the web app behind Caddy with automatic HTTPS. Set `POSTGRES_PASSWORD`, `FP_SECRET_KEY` and `FP_DOMAIN` first (see `.env.example`).
