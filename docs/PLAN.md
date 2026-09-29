# FloorPulse build plan

Each phase ends with: tests green, app run and exercised in a browser (Playwright screenshots at 390px and 1280px), acceptance criteria verified, a tagged commit (`phase-N`).

## Phase 0: Foundation
- Repo skeleton, `.gitignore`, `.env.example`, Makefile, pre-commit, GitHub Actions CI.
- Backend: FastAPI app factory, pydantic-settings config, JSON logging with request IDs, error envelope, security headers, CORS, request size limit.
- DB: SQLAlchemy 2 typed models, base mixins (`organization_id`, timestamps, `created_by`, `archived_at`), Alembic with a reversible initial migration.
- Tenancy: `organizations`, `sites`, `areas`, `users`, `user_roles`, `user_sites`, `devices`, `refresh_tokens`, `settings`, `audit_log`. A single `get_current_user` dependency provides the org scope; the `scoped()` helper filters every query.
- Auth: argon2 passwords, 15 min JWT access token (Bearer), rotating 30-day refresh token in an httpOnly cookie with reuse detection, CSRF double-submit on cookie endpoints, PIN login (4-6 digits, per-device, rate-limited), optional TOTP for admin/manager, role dependency `require_roles`.
- Audit-log service, `/healthz`, `/readyz`, `/metrics`.
- Tests: auth flows, tenant isolation, role checks, audit log.
- Frontend: Vite + React 18 + TS, Tailwind with design tokens (status colours, dark theme), React Router, TanStack Query, i18next (en, hi, RTL-ready), API client with refresh handling, OpenAPI type generation, operator shell (PIN login, dark) and manager shell (password login, sidebar).
- Acceptance: dev servers run, every role logs in, tenant isolation tests pass, lint/types/tests green.

## Phase 1: MVP (machines, shifts, downtime, production)
- Models: shifts, shift_calendar, holidays, machines, downtime reason groups/reasons, downtime_events, products, production_orders, production_entries, defect categories/types, defect_entries, shift_runs.
- Master-data CRUD with CSV/XLSX import (row-by-row error report) and export; soft-delete.
- Shift engine: resolve shift for a timestamp in the site's time zone, overnight and DST-safe; tests.
- Downtime: stop/resume (server timestamps, client timestamps kept), one open event per machine (partial unique index + app check), idempotency by `client_uuid`, auto-close at shift end with `needs_review`, split/edit/back-fill with audit.
- Production and defect quick entry with idempotency.
- SSE stream for machine status (polling fallback on the client).
- Operator PWA: machine grid, machine screen, stop flow (reason grid, recent first, undo 10 s), output stepper, defect entry; IndexedDB outbox with retries; reference-data cache; service worker (Workbox via vite-plugin-pwa); manifest and icons.
- Manager dashboard: live status, output, downtime Pareto, defects.
- Seed: deterministic demo org (2 sites, 6 lines, 25 machines, 3 shifts, 60 days, 12 users).
- Playwright: offline stop + output then sync; dashboard update.
- `docs/DEMO.md`.

## Phase 2: OEE and analytics
- Pure OEE service (A, P, Q, OEE, TEEP, six big losses), interval-clipping to period boundaries, overlap rule; exhaustive unit tests.
- Daily/shift aggregate tables rebuilt by a job and on demand.
- MTBF, MTTR, scrap rate, FPY, on-time completion, cost of downtime.
- Shift review (timeline, unexplained gaps, assign reasons, close shift + handover).
- Dashboard: period selector + previous-period comparison, formula drawer, chart table view toggle, PNG/CSV export, drill-downs.
- Benchmark seed (1M rows) and timing script.

## Phase 3: Inventory and procurement
- Materials, locations, lots, append-only stock ledger, cached balances + reconciliation job, negative-stock guard.
- BOM, release shortage check, backflush.
- Reorder alerts, days of cover, suggested purchase list.
- Suppliers, purchase requests -> approval -> PO -> goods receipt (partial).
- Stock counts with variance approval; FEFO suggestions; valuation and ageing.
- Traceability both directions; QR label PDF sheets; camera scan route.
- Property-based test (hypothesis) that balances equal ledger sums.

## Phase 4: Quality
- Defect dispositions and rework re-inspection.
- Inspection plans/characteristics/results; out-of-spec alert and hold.
- NCR workflow with actions.
- SPC: X-bar/R and individuals charts, Cp/Cpk, Western Electric rules 1 and trend; verified against a reference dataset.
- Supplier quality, customer complaints.

## Phase 5: Maintenance
- Work orders with state machine, time entries, parts used (stock deduction).
- One-tap breakdown -> WO; completion updates the downtime cause.
- PM schedules (calendar/hours/count) with checklists; generator job; overdue escalation; compliance %.
- Asset history, bad-actor ranking.
- Ingest endpoint with per-machine API keys; `scripts/simulate_gateway.py`.

## Phase 6: Alerts, reports, integrations
- Alert rule engine with dedup window, quiet hours, acknowledgement + comments.
- `NotificationChannel` interface: in-app, web push, SMTP, WhatsApp/Twilio, console.
- Daily digest and weekly summary.
- Report pack with PDF/XLSX/CSV export, scheduled reports, share links, `/tv/:token` andon mode, API keys, `docs/API.md`.

## Phase 7: Hardening and launch
- Security review, load test, axe accessibility checks, Hindi pass.
- Onboarding wizard and industry templates.
- `docs/USER_GUIDE.md` (screenshots via Playwright), `docs/OPERATIONS.md`, `docs/INTEGRATIONS.md`.
