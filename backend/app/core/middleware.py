import logging
import time
import uuid

from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Match

from app.core.errors import envelope
from app.core.logging import client_ip_var, request_id_var

log = logging.getLogger("floorpulse.request")

REQUESTS = Counter("fp_http_requests_total", "HTTP requests", ["method", "route", "status"])
LATENCY = Histogram("fp_http_request_seconds", "HTTP request latency", ["method", "route"])

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}


def _route_template(request: Request) -> str:
    for route in request.app.router.routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            return getattr(route, "path", request.url.path)
    return "unmatched"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Request ID, size limit, security headers, access log and metrics."""

    def __init__(self, app: object, max_body: int) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.max_body = max_body

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        token = request_id_var.set(rid)
        client_ip_var.set(request.client.host if request.client else None)
        start = time.perf_counter()
        try:
            length = request.headers.get("content-length")
            if length and length.isdigit() and int(length) > self.max_body:
                response: Response = envelope(413, "payload_too_large", "Request body too large")
            else:
                response = await call_next(request)
            elapsed = time.perf_counter() - start
            route = _route_template(request)
            if route != "/api/v1/stream":
                REQUESTS.labels(request.method, route, response.status_code).inc()
                LATENCY.labels(request.method, route).observe(elapsed)
            response.headers["X-Request-ID"] = rid
            for k, v in SECURITY_HEADERS.items():
                response.headers.setdefault(k, v)
            if request.url.scheme == "https":
                response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
            log.info(
                "request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "ms": round(elapsed * 1000, 1),
                },
            )
            return response
        finally:
            request_id_var.reset(token)
