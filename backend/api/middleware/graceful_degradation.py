"""
backend/api/middleware/graceful_degradation.py

Centralised circuit-breaker pattern for all external service calls.
Wraps calls to LLM, Vector DB, and MCP/OSM with:
  - Timeout enforcement
  - Exception catching with structured logging
  - Consistent fallback return values

Usage:
    from backend.api.middleware.graceful_degradation import safe_call, ServiceUnavailable

    result = await safe_call(
        coro=my_async_function(args),
        service_name="GroqLLM",
        fallback="I am temporarily unavailable. Please try again shortly.",
        timeout_s=8.0,
    )
"""
import asyncio
import functools
import logging
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ServiceUnavailable(Exception):
    """Raised when a downstream service is unreachable and no fallback is specified."""
    def __init__(self, service: str, reason: str) -> None:
        super().__init__(f"[{service}] unavailable: {reason}")
        self.service = service
        self.reason = reason


async def safe_call(
    coro: Any,
    *,
    service_name: str,
    fallback: Optional[T] = None,
    timeout_s: float = 10.0,
    raise_on_failure: bool = False,
) -> T:
    """
    Awaits `coro` with a timeout. On any exception (timeout, connection error,
    API error, etc.) logs a warning and returns `fallback` instead of propagating.

    Args:
        coro:             An awaitable (coroutine).
        service_name:     Human-readable name for logging (e.g. "GroqLLM", "Qdrant", "OSM").
        fallback:         Value to return when the call fails. Default: None.
        timeout_s:        Seconds before an asyncio.TimeoutError is triggered. Default: 10.
        raise_on_failure: If True, raises ServiceUnavailable instead of returning fallback.

    Returns:
        The coroutine result on success, or `fallback` on failure.
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout_s)
    except asyncio.TimeoutError:
        logger.warning(
            "[%s] timed out after %.1fs — using fallback",
            service_name, timeout_s,
        )
    except ConnectionError as exc:
        logger.warning("[%s] connection error: %s — using fallback", service_name, exc)
    except Exception as exc:
        logger.warning("[%s] unexpected error: %s — using fallback", service_name, exc)

    if raise_on_failure:
        raise ServiceUnavailable(service_name, "call failed — see logs above")
    return fallback  # type: ignore[return-value]


def safe_sync(
    func: Callable[..., T],
    *args: Any,
    service_name: str,
    fallback: Optional[T] = None,
    **kwargs: Any,
) -> T:
    """
    Synchronous version of safe_call. Wraps a blocking function call.
    Use for synchronous DB queries, embedding calls, etc.
    """
    try:
        return func(*args, **kwargs)
    except Exception as exc:
        logger.warning("[%s] error: %s — using fallback", service_name, exc)
        return fallback  # type: ignore[return-value]


# ── Pre-configured wrappers for each external service ────────────────────────

async def safe_llm_call(coro: Any, fallback: str = "I'm temporarily unavailable. Please try again.") -> str:
    """Wrapper for Groq LLM calls — 12s timeout, conversational fallback."""
    return await safe_call(coro, service_name="GroqLLM", fallback=fallback, timeout_s=12.0)


async def safe_qdrant_call(coro: Any, fallback: list = None) -> list:
    """Wrapper for Qdrant vector search — 6s timeout, empty-list fallback."""
    return await safe_call(
        coro, service_name="Qdrant", fallback=fallback if fallback is not None else [], timeout_s=6.0
    )


async def safe_osm_call(coro: Any) -> list:
    """Wrapper for OSM/MCP amenity calls — 8s timeout, empty list on failure."""
    return await safe_call(coro, service_name="OSM-MCP", fallback=[], timeout_s=8.0)


def safe_db_call(func: Callable[..., T], *args: Any, **kwargs: Any) -> Optional[T]:
    """Wrapper for synchronous SQLAlchemy DB calls — returns None on failure."""
    return safe_sync(func, *args, service_name="PostgreSQL", fallback=None, **kwargs)
