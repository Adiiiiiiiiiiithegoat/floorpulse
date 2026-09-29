# API

REST under `/api/v1`. The OpenAPI schema is at `/api/v1/openapi.json` with interactive docs at `/docs`. TypeScript types for the frontend are generated from it (`npm run gen:api`), and CI fails if they are stale.

## Conventions

- **Auth:** `Authorization: Bearer <access token>` (15 min JWT). The refresh token is an httpOnly cookie scoped to `/api/v1/auth`. Cookie endpoints need the `X-CSRF-Token` header echoing the `fp_csrf` cookie.
- **Errors:** always `{"error": {"code", "message", "details"}}`. Codes are stable and machine-readable (`invalid_credentials`, `not_found`, `validation_error`, `stale_record`, `rate_limited`, …).
- **Pagination:** list endpoints that can grow take `page` and `page_size` (max 500) and return `{items, total, page, page_size}`.
- **Concurrency:** editable records return `ETag`; send `If-Match` to get `412 stale_record` instead of overwriting someone else's change.
- **Tenancy and roles:** enforced server-side on every route. Foreign rows return 404; missing roles return 403. `admin` passes every role check.
- **Rate limits:** login, PIN login, refresh and device lookup are rate-limited per IP (and per account for login).

## Endpoints (Phase 0)

| Method | Path | Who | Notes |
|---|---|---|---|
| GET | `/healthz`, `/readyz`, `/metrics` | public | liveness, DB readiness, Prometheus |
| POST | `/auth/login` | public | email + password (+ `totp_code` when 2FA is on) |
| GET | `/auth/device` | device | `X-Device-Token`; site info + operators who can PIN in |
| POST | `/auth/pin-login` | device | `{user_id, pin}`; 5 wrong PINs lock the user for 5 minutes |
| POST | `/auth/refresh` | cookie | rotates the refresh token |
| POST | `/auth/logout` | cookie | revokes the session |
| GET | `/me` | any | current user |
| GET, DELETE | `/me/sessions`, `/me/sessions/{id}` | any | signed-in devices, remote logout |
| POST | `/me/pin`, `/me/password` | any | change own credentials |
| POST | `/me/totp/setup`, `/enable`, `/disable` | any | TOTP 2FA |
| POST, DELETE | `/devices`, `/devices/{id}` | supervisor, manager | register or revoke a shop-floor device |
| GET, PUT | `/org/settings` | any / admin | organization settings |
| GET, POST, GET, PATCH | `/sites`, `/sites/{id}` | any (read) / admin | archive with `{"archived": true}` |
| GET, POST, PATCH | `/areas`, `/areas/{id}` | any (read) / admin | lines |
| GET | `/users` | supervisor, manager | filter `q`, `role`, `active` |
| POST, GET, PATCH | `/users`, `/users/{id}` | admin | deactivate with `{"is_active": false}` (revokes sessions) |
| POST | `/users/{id}/logout-all` | admin | |
| GET | `/audit` | manager | filter by entity, actor, action prefix, time range |
