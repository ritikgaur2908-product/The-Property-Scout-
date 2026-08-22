"""
backend/api/middleware/rate_limiter.py

Per-session and per-IP sliding-window rate limiting using a pure in-memory
token bucket. No Redis dependency — works out of the box.

Two independent limiters:
  • IP limiter  — 60 requests / 60 s per client IP (global abuse guard)
  • Session limiter — 30 requests / 60 s per session_id (fair-use per conversation)

WebSocket connections (/api/voice/*) are exempt from request-level rate
limiting because they maintain a persistent connection and are already
constrained by the STT/LLM pipeline latency.

Configuration via environment variables (all optional, defaults shown):
  RATE_LIMIT_IP_MAX        = 60    (requests)
  RATE_LIMIT_IP_WINDOW_S   = 60    (seconds)
  RATE_LIMIT_SES_MAX       = 30    (requests)
  RATE_LIMIT_SES_WINDOW_S  = 60    (seconds)
"""
import logging
import os
import time
from collections import deque, defaultdict
from threading import Lock
from typing import Deque, Dict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────
_IP_MAX    = int(os.getenv("RATE_LIMIT_IP_MAX",      "60"))
_IP_WIN    = int(os.getenv("RATE_LIMIT_IP_WINDOW_S", "60"))
_SES_MAX   = int(os.getenv("RATE_LIMIT_SES_MAX",     "30"))
_SES_WIN   = int(os.getenv("RATE_LIMIT_SES_WINDOW_S","60"))

# Paths that are completely exempt from rate limiting
_EXEMPT_PREFIXES = (
    "/api/voice",    # WebSocket — persistent connection, exempt
    "/api/health",   # Health checks — must never be blocked
    "/docs",         # OpenAPI docs
    "/openapi.json",
)


class _SlidingWindow:
    """Thread-safe sliding-window counter using a timestamped deque."""

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self._max = max_requests
        self._win = window_seconds
        self._buckets: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def is_allowed(self, key: str) -> tuple[bool, int]:
        """
        Returns (allowed, retry_after_seconds).
        `retry_after_seconds` is 0 when allowed.
        """
        now = time.monotonic()
        cutoff = now - self._win

        with self._lock:
            dq = self._buckets[key]
            # Evict timestamps outside the window
            while dq and dq[0] < cutoff:
                dq.popleft()

            if len(dq) >= self._max:
                # Oldest request in window determines when a slot opens
                retry_after = int(self._win - (now - dq[0])) + 1
                return False, retry_after

            dq.append(now)
            return True, 0

    def cleanup_stale(self) -> None:
        """Evict keys with no recent activity (call periodically)."""
        now = time.monotonic()
        cutoff = now - self._win
        with self._lock:
            stale = [k for k, dq in self._buckets.items() if not dq or dq[-1] < cutoff]
            for k in stale:
                del self._buckets[k]


_ip_limiter  = _SlidingWindow(_IP_MAX,  _IP_WIN)
_ses_limiter = _SlidingWindow(_SES_MAX, _SES_WIN)

# Cleanup counter — prune stale keys every ~500 requests
_cleanup_counter = 0


def _get_client_ip(request: Request) -> str:
    """Extract real client IP, respecting X-Forwarded-For from proxies."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _get_session_id(request: Request) -> str | None:
    """
    Extract session_id from:
      1. Path parameter  — /api/session/{session_id}/...
      2. Query parameter — ?session_id=...
      3. Header          — X-Session-ID
    """
    # Path-based: /api/session/<uuid>/...
    path_parts = request.url.path.split("/")
    if "session" in path_parts:
        idx = path_parts.index("session")
        if idx + 1 < len(path_parts) and len(path_parts[idx + 1]) >= 8:
            return path_parts[idx + 1]

    # Query param
    sid = request.query_params.get("session_id")
    if sid:
        return sid

    # Header
    return request.headers.get("X-Session-ID")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding-window rate limiter middleware for FastAPI.
    Applied per-IP (global guard) and per-session (fair-use).
    WebSocket and health-check routes are exempt.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        global _cleanup_counter

        path = request.url.path

        # ── Exempt certain paths ───────────────────────────────────────────
        if any(path.startswith(prefix) for prefix in _EXEMPT_PREFIXES):
            return await call_next(request)

        client_ip = _get_client_ip(request)
        session_id = _get_session_id(request)

        # ── IP-level check ─────────────────────────────────────────────────
        ip_ok, ip_retry = _ip_limiter.is_allowed(client_ip)
        if not ip_ok:
            logger.warning(
                "Rate limit exceeded (IP): %s on %s — retry after %ds",
                client_ip, path, ip_retry,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": (
                        f"Too many requests from your IP address. "
                        f"Please wait {ip_retry} seconds before trying again."
                    ),
                    "retry_after": ip_retry,
                },
                headers={"Retry-After": str(ip_retry)},
            )

        # ── Session-level check ────────────────────────────────────────────
        if session_id:
            ses_ok, ses_retry = _ses_limiter.is_allowed(session_id)
            if not ses_ok:
                logger.warning(
                    "Rate limit exceeded (session): %s on %s — retry after %ds",
                    session_id[:8], path, ses_retry,
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "rate_limit_exceeded",
                        "message": (
                            f"You're sending messages too quickly. "
                            f"Please wait {ses_retry} seconds."
                        ),
                        "retry_after": ses_retry,
                    },
                    headers={"Retry-After": str(ses_retry)},
                )

        # ── Periodic cleanup ───────────────────────────────────────────────
        _cleanup_counter += 1
        if _cleanup_counter % 500 == 0:
            _ip_limiter.cleanup_stale()
            _ses_limiter.cleanup_stale()

        response = await call_next(request)

        # Attach rate-limit info headers on successful responses
        response.headers["X-RateLimit-IP-Limit"]  = str(_IP_MAX)
        response.headers["X-RateLimit-Ses-Limit"] = str(_SES_MAX)

        return response
