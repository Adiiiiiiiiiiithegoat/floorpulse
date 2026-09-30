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

## Demo credentials

> These exist only in the seeded demo organization (`python -m app.seed`). Never use them in production.

Organization: **Demo Auto Components Pvt Ltd**, with two plants: **Pune Plant** (`PUN`: Machining Line, Press Shop, Assembly Line) and **Chennai Plant** (`CHE`: Moulding Line, CNC Cell, Packing Line).

- Password for every email login: **`FloorPulse!2026`**
- PIN for every shop-floor user: **`1234`**

### Manager / staff app: http://localhost:5173/login

| Name | Email | Role(s) | Plants | PIN |
|---|---|---|---|---|
| Anita Desai | `admin@demo.floorpulse.app` | Admin | Pune, Chennai | — |
| Rajesh Kumar | `manager@demo.floorpulse.app` | Plant manager | Pune, Chennai | — |
| Suresh Patil | `supervisor.pune@demo.floorpulse.app` | Supervisor | Pune | `1234` |
| Meena Iyer | `supervisor.chennai@demo.floorpulse.app` | Supervisor | Chennai | `1234` |
| Vikram Singh | `tech@demo.floorpulse.app` | Maintenance technician | Pune, Chennai | `1234` |
| Arjun Nair | `tech2@demo.floorpulse.app` | Technician + operator | Chennai | `1234` |
| Priya Sharma | `quality@demo.floorpulse.app` | Quality inspector | Pune, Chennai | `1234` |
| Farhan Shaikh | `stores@demo.floorpulse.app` | Store keeper | Pune, Chennai | `1234` |

### Operator app (PIN only): http://localhost:5173/floor

| Name | Employee code | Plant | PIN |
|---|---|---|---|
| Ganesh Jadhav | E101 | Pune | `1234` |
| Lakshmi Rao | E102 | Pune | `1234` |
| Mohan Das | E103 | Chennai | `1234` |
| Kavita Joshi | E104 | Chennai | `1234` |

Staff with a PIN (supervisors, technicians, inspector, store keeper) can also sign in on a device at their plant.

### Shop-floor devices

PIN sign-in only works on a registered device. Pick one of these:

1. **Use a seeded demo device.** Open the browser console (F12) on the app and run one of these, then open `/floor`:
   - Pune: `localStorage.setItem('fp_device_token', 'demo-device-pun')`
   - Chennai: `localStorage.setItem('fp_device_token', 'demo-device-che')`
2. **Register a real device.** Open `/floor` on the phone, sign in as a supervisor (for example `supervisor.pune@demo.floorpulse.app` / `FloorPulse!2026`), and choose the plant and line.

To switch a browser back to an unregistered device, run `localStorage.removeItem('fp_device_token')`.

### Useful URLs (local)

| What | URL |
|---|---|
| Manager / staff sign-in | http://localhost:5173/login |
| Operator app | http://localhost:5173/floor |
| Device setup | http://localhost:5173/floor/setup |
| API docs (Swagger) | http://localhost:8000/docs |
| Health / metrics | http://localhost:8000/healthz, http://localhost:8000/metrics |

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
