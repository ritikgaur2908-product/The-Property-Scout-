import httpx
import logging
import asyncio
from backend.config import settings

logger = logging.getLogger("webhook-dispatcher")

_PLACEHOLDER_HOSTS = ("n8n.example.com", "example.com")


def is_webhook_configured() -> bool:
    base_url = (settings.N8N_WEBHOOK_BASE_URL or "").strip()
    if not base_url:
        return False
    return not any(host in base_url for host in _PLACEHOLDER_HOSTS)


def _webhook_path(event_type: str) -> str:
    return (
        settings.N8N_BOOKING_WEBHOOK_PATH
        if "booking" in event_type
        else settings.N8N_SHORTLIST_WEBHOOK_PATH
    )


async def _send_webhook_async(event_type: str, payload: dict, path: str) -> bool:
    base_url = settings.N8N_WEBHOOK_BASE_URL
    if not base_url or not is_webhook_configured():
        logger.warning("Webhook omitted for %s - N8N is not configured.", event_type)
        return False

    url = f"{base_url.rstrip('/')}{path}"
    
    # Simple retry logic (up to 3 attempts)
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                logger.info("Webhook %s dispatched successfully to %s", event_type, url)
                return True
        except Exception as e:
            logger.warning("Webhook attempt %s failed for %s: %s", attempt, event_type, e)
            if attempt < max_attempts:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff: 2s, 4s
            else:
                logger.error("Failed to dispatch webhook %s after %s attempts.", event_type, max_attempts)
    return False

def trigger_webhook_sync(event_type: str, payload: dict) -> bool:
    """Dispatch a webhook synchronously and return whether it succeeded."""
    path = _webhook_path(event_type)
    try:
        loop = asyncio.get_running_loop()
        future = asyncio.run_coroutine_threadsafe(
            _send_webhook_async(event_type, payload, path), loop
        )
        return bool(future.result(timeout=15))
    except RuntimeError:
        return asyncio.run(_send_webhook_async(event_type, payload, path))
    except Exception as exc:
        logger.error("Sync webhook dispatch failed for %s: %s", event_type, exc)
        return False


def trigger_webhook(event_type: str, payload: dict):
    """
    Fire-and-forget webhook dispatcher.
    Runs the asynchronous dispatch in the background event loop.
    """
    path = _webhook_path(event_type)
    
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_send_webhook_async(event_type, payload, path))
    except RuntimeError:
        asyncio.run(_send_webhook_async(event_type, payload, path))
