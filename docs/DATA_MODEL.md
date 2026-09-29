# Data model

Conventions:
- Every business table carries `organization_id` and is read through `scoped()` / `get_owned()` in `app/core/deps.py`. Another tenant's row looks like a missing one (404).
- Standard columns: `id`, `organization_id`, `created_at`, `updated_at`, `created_by`, plus `archived_at` where rows can be retired. Rows with history are archived, never deleted.
- Times are stored as UTC through the `UTCDateTime` column type (naive UTC in the database, aware UTC in Python) and shown in the site's time zone.
- Constraint names follow a fixed naming convention so Alembic batch migrations work on SQLite.

## Phase 0: tenancy, identity, audit

| Table | Purpose | Notes |
|---|---|---|
| `organizations` | Tenant | `settings` JSON validated by `OrgSettings` (time zone, currency, thresholds, privacy switches) |
| `sites` | Plant | `timezone` (IANA), unique `(organization_id, code)` |
| `areas` | Line / production area in a site | unique `(site_id, code)` |
| `users` | People | `email` globally unique (nullable for PIN-only operators); `employee_code` unique per org (badge QR); argon2 `password_hash` and `pin_hash`; `pin_length`; PIN lockout counters; TOTP secret |
| `user_roles` | Role membership | PK `(user_id, role)`; roles: operator, supervisor, technician, inspector, storekeeper, manager, admin |
| `user_sites` | Site access | Non-admins see only assigned sites |
| `devices` | Registered shop-floor devices | Only `sha256(token)` is stored; `revoked_at` |
| `refresh_tokens` | One row per issued refresh token | `family_id` = one login session; rotation marks `used_at`; reuse outside a 15 s race window revokes the family |
| `audit_log` | Append-only change history | `before`/`after` JSON with secrets redacted, actor, IP, request ID |
| `job_runs` | Scheduled job history | status `running`/`ok`/`error` |
