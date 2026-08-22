import logging
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from backend.db.models import Booking, Property
from backend.booking.id_generator import generate_unique_booking_id, generate_unique_user_id
from backend.booking.concurrency import get_alternative_slots
from backend.notification.payloads import build_booking_payload
from backend.notification.webhook import trigger_webhook

logger = logging.getLogger(__name__)

class BookingConflictError(Exception):
    def __init__(self, alternative_slots):
        self.alternative_slots = alternative_slots
        super().__init__("Booking slot is already taken.")

class BookingNotFoundError(Exception):
    pass

def create_booking(db: Session, property_id: str, email: str, visit_date_str: str, visit_time_str: str) -> dict:
    # Ensure property exists and lock the row to prevent concurrent bookings
    prop = db.query(Property).filter(Property.id == property_id).with_for_update().first()
    if not prop:
        raise ValueError("Property not found")
        
    visit_date = datetime.strptime(visit_date_str, "%Y-%m-%d").date()
    visit_time = datetime.strptime(visit_time_str, "%H:%M:%S").time()

    # Check if this specific slot is already taken
    existing = db.query(Booking).filter(
        Booking.property_id == property_id,
        Booking.visit_date == visit_date,
        Booking.visit_time == visit_time,
        Booking.status != "cancelled"
    ).first()
    
    if existing:
        alt_slots = get_alternative_slots(db, property_id, visit_date)
        raise BookingConflictError(alt_slots)

    booking_id = generate_unique_booking_id(db)
    user_id = generate_unique_user_id(db)

    new_booking = Booking(
        booking_id=booking_id,
        user_id=user_id,
        property_id=property_id,
        user_email=email,
        visit_date=visit_date,
        visit_time=visit_time,
        status="confirmed"
    )

    try:
        db.add(new_booking)
        db.commit()
        db.refresh(new_booking)
        
        # Trigger Webhook
        payload = build_booking_payload("booking_created", new_booking, prop)
        trigger_webhook("booking_created", payload)
        
        return new_booking
    except IntegrityError:
        db.rollback()
        alt_slots = get_alternative_slots(db, property_id, visit_date)
        raise BookingConflictError(alt_slots)

def get_booking(db: Session, booking_id: str) -> Booking:
    booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
    if not booking:
        # Fallback: fuzzy search by prefix if exact match fails (e.g. truncated ID)
        matches = db.query(Booking).filter(Booking.booking_id.startswith(booking_id)).all()
        if len(matches) == 1:
            return matches[0]
        raise BookingNotFoundError()
    return booking

def reschedule_booking(db: Session, booking_id: str, new_date_str: str, new_time_str: str) -> Booking:
    base_booking = get_booking(db, booking_id)
    booking = db.query(Booking).filter(Booking.booking_id == base_booking.booking_id).with_for_update().first()
    if not booking:
        raise BookingNotFoundError()
        
    if booking.status == "cancelled":
        raise ValueError("Cannot reschedule a cancelled booking")

    new_date = datetime.strptime(new_date_str, "%Y-%m-%d").date()
    new_time = datetime.strptime(new_time_str, "%H:%M:%S").time()

    # Check for conflict
    existing = db.query(Booking).filter(
        Booking.property_id == booking.property_id,
        Booking.visit_date == new_date,
        Booking.visit_time == new_time,
        Booking.status != "cancelled"
    ).first()
    
    if existing and existing.id != booking.id:
        alt_slots = get_alternative_slots(db, booking.property_id, new_date)
        raise BookingConflictError(alt_slots)

    booking.visit_date = new_date
    booking.visit_time = new_time
    booking.status = "rescheduled"

    try:
        db.commit()
        db.refresh(booking)
        
        # Trigger Webhook
        prop = db.query(Property).filter(Property.id == booking.property_id).first()
        payload = build_booking_payload("booking_rescheduled", booking, prop)
        trigger_webhook("booking_rescheduled", payload)
        
        return booking
    except IntegrityError:
        db.rollback()
        alt_slots = get_alternative_slots(db, booking.property_id, new_date)
        raise BookingConflictError(alt_slots)

def cancel_booking(db: Session, booking_id: str) -> Booking:
    booking = get_booking(db, booking_id)
        
    booking.status = "cancelled"
    db.commit()
    db.refresh(booking)
    
    # Trigger Webhook
    prop = db.query(Property).filter(Property.id == booking.property_id).first()
    payload = build_booking_payload("booking_cancelled", booking, prop)
    trigger_webhook("booking_cancelled", payload)
    
    return booking
