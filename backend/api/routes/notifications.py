from fastapi import APIRouter
import logging
from backend.notification.payloads import build_shortlist_payload
from backend.notification.webhook import trigger_webhook
from backend.api.middleware.validation import ShortlistEmailRequest

logger = logging.getLogger("routes-notifications")
router = APIRouter(tags=["Notifications"])

@router.post("/shortlist")
async def notify_shortlist(payload: ShortlistEmailRequest):
    """
    Email the current shortlist to the user via the N8N webhook.
    Accepts a validated email and the list of enriched property objects.
    """
    logger.info(
        "Triggering shortlist notification to %s with %d properties.",
        payload.email, len(payload.shortlist),
    )
    try:
        webhook_payload = build_shortlist_payload(payload.email, payload.shortlist)
        trigger_webhook("shortlist_mailed", webhook_payload)
        return {
            "status": "success",
            "message": f"Shortlist notification queued for {payload.email}.",
            "properties_sent": len(payload.shortlist),
        }
    except Exception as e:
        logger.error("Failed to trigger shortlist webhook: %s", e)
        return {
            "status": "error",
            "message": "Failed to queue the email. Please try again in a moment.",
        }
