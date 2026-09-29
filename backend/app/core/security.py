import hashlib
import secrets
import time
from collections import deque
from datetime import timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.time import utcnow

# Cheap parameters in tests only; production uses argon2-cffi defaults (RFC 9106 low-memory profile).
_hasher = (
    PasswordHasher(time_cost=1, memory_cost=1024, parallelism=1)
    if get_settings().env == "test"
    else PasswordHasher()
)
_ALGO = "HS256"


def hash_secret(plain: str) -> str:
    return _hasher.hash(plain)


def verify_secret(hashed: str | None, plain: str) -> bool:
    if not hashed:
        # Burn comparable time so absent hashes are not distinguishable by timing.
        _hasher.hash(plain)
        return False
    try:
        return _hasher.verify(hashed, plain)
    except (VerificationError, InvalidHashError):
        return False


def create_access_token(
    user_id: int, org_id: int, roles: list[str], device_id: int | None = None, session_id: str | None = None
) -> str:
    s = get_settings()
    now = utcnow()
    claims: dict[str, Any] = {
        "sub": str(user_id),
        "org": org_id,
        "roles": roles,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=s.access_token_minutes)).timestamp()),
        "typ": "access",
    }
    if device_id is not None:
        claims["dev"] = device_id
    if session_id is not None:
        claims["sid"] = session_id
    return jwt.encode(claims, s.secret_key, algorithm=_ALGO)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        claims: dict[str, Any] = jwt.decode(token, get_settings().secret_key, algorithms=[_ALGO])
    except jwt.ExpiredSignatureError as e:
        raise AppError(401, "token_expired", "Access token expired") from e
    except jwt.PyJWTError as e:
        raise AppError(401, "invalid_token", "Invalid access token") from e
    if claims.get("typ") != "access":
        raise AppError(401, "invalid_token", "Invalid access token")
    return claims


def new_opaque_token() -> str:
    return secrets.token_urlsafe(32)


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class RateLimiter:
    """Sliding-window limiter, in-process. See DECISIONS.md #5 for the ceiling."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}

    def check(self, key: str, limit: int, window_s: float) -> None:
        now = time.monotonic()
        q = self._hits.setdefault(key, deque())
        while q and q[0] <= now - window_s:
            q.popleft()
        if len(q) >= limit:
            retry = int(window_s - (now - q[0])) + 1
            raise AppError(
                429, "rate_limited", "Too many attempts, try again shortly", {"retry_after": retry}
            )
        q.append(now)

    def reset(self) -> None:
        self._hits.clear()


limiter = RateLimiter()
