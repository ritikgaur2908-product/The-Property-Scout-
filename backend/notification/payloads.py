from backend.db.models import Booking, Property
from typing import List, Dict

def build_booking_payload(event_type: str, booking: Booking, property_obj: Property) -> dict:
    """
    Builds a JSON-serializable payload for booking events.
    event_type can be: 'booking_created', 'booking_rescheduled', 'booking_cancelled'
    """
    return {
        "event": event_type,
        "booking": {
            "booking_id": booking.booking_id,
            "user_id": booking.user_id,
            "user_email": booking.user_email,
            "visit_date": booking.visit_date.isoformat() if booking.visit_date else None,
            "visit_time": booking.visit_time.isoformat() if booking.visit_time else None,
            "status": booking.status
        },
        "property": {
            "id": str(property_obj.id),
            "address": property_obj.address,
            "locality": property_obj.locality,
            "rent": property_obj.rent,
            "bhk": property_obj.rooms,
            "accommodation_type": property_obj.accommodation_type
        }
    }

def build_shortlist_payload(email: str, properties: List[Dict]) -> dict:
    """
    Builds a JSON-serializable payload for shortlist mailing.
    `properties` is expected to be a list of dictionaries (from the orchestrator/RAG state).
    """
    return {
        "event": "shortlist_mailed",
        "user_email": email,
        "shortlist_count": len(properties),
        "properties": properties
    }
