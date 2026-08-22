import random
from sqlalchemy.orm import Session
from backend.db.models import Booking

def generate_random_id(prefix: str, length: int = 6) -> str:
    suffix = "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=length))
    return f"{prefix}-{suffix}"

def generate_unique_booking_id(db: Session) -> str:
    """Generate a unique BK-XXXXXX id."""
    while True:
        candidate = generate_random_id("BK")
        if not db.query(Booking).filter(Booking.booking_id == candidate).first():
            return candidate

def generate_unique_user_id(db: Session) -> str:
    """Generate a unique USR-XXXXXX id."""
    while True:
        candidate = generate_random_id("USR")
        if not db.query(Booking).filter(Booking.user_id == candidate).first():
            return candidate
