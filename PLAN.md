# FloorPulse: plan

## Phase 0: Foundation
- [x] FastAPI + SQLAlchemy 2 + Alembic backend with tenancy and audit log
- [x] Auth: argon2, rotating refresh tokens, CSRF, device-bound PIN login, TOTP
- [x] React operator and manager shells with i18n and generated API types
- [x] CI green: lint, types, backend tests, Playwright tests, Postgres migrations
- [x] Public repo, phase-0 tag, README with demo logins

## Next phases (detail in docs/PLAN.md)
- [ ] Phase 1: machines, shifts, downtime, production entry, offline operator PWA
- [ ] Phase 2: OEE, MTBF/MTTR, shift review and analytics dashboard
- [ ] Phase 3: inventory, BOM and procurement
- [ ] Phase 4: quality (inspections, NCRs, SPC)
- [ ] Phase 5: maintenance work orders and PM schedules
- [ ] Phase 6: alerts, reports and integrations
- [ ] Phase 7: hardening, onboarding wizard and user docs

## Launch
- [ ] First real run of docker compose (Postgres + API + Caddy HTTPS); never tested, no Docker on the build machine
- [ ] Set a real FP_SECRET_KEY and domain, and don't reuse the public demo credentials
