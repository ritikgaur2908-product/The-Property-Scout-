from datetime import date, time, timedelta
from typing import List
from sqlalchemy.orm import Session
from backend.db.models import Booking

def get_alternative_slots(db: Session, property_id: str, visit_date: date) -> List[str]:
    """
    Returns available time slots for a given property and date.
    Assumes standard slots from 10:00 to 17:00 (10 AM to 5 PM).
    """
    all_slots = [
        "10:00:00", "11:00:00", "12:00:00", 
        "14:00:00", "15:00:00", "16:00:00", "17:00:00"
    ]
    
    # Find taken slots
    taken_bookings = db.query(Booking.visit_time).filter(
        Booking.property_id == property_id,
        Booking.visit_date == visit_date,
        Booking.status != "cancelled"
    ).all()
    
    taken_times = {b[0].strftime("%H:%M:%S") for b in taken_bookings}
    
    available = [slot for slot in all_slots if slot not in taken_times]
    return available
