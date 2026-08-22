from fastapi import APIRouter, Depends, HTTPException, status
import logging
from sqlalchemy.orm import Session
from backend.db.connection import get_db
from backend.booking import service
from backend.booking.service import BookingConflictError, BookingNotFoundError
from backend.api.middleware.validation import CreateBookingRequest, RescheduleBookingRequest

logger = logging.getLogger("routes-bookings")
router = APIRouter(tags=["Bookings"])

@router.post("")
async def create_booking_endpoint(payload: CreateBookingRequest, db: Session = Depends(get_db)):
    """
    Create a new booking (returns booking_id + user_id).
    Enforces uniqueness: one property can only be booked once per date+time slot.
    """
    logger.info(
        "Creating booking: property=%s, email=%s, date=%s, time=%s",
        payload.property_id, payload.email, payload.visit_date, payload.visit_time,
    )
    try:
        booking = service.create_booking(
            db, payload.property_id, payload.email, payload.visit_date, payload.visit_time
        )
        return {
            "id": str(booking.id),
            "booking_id": booking.booking_id,
            "user_id": booking.user_id,
            "property_id": str(booking.property_id),
            "user_email": booking.user_email,
            "visit_date": str(booking.visit_date),
            "visit_time": str(booking.visit_time),
            "status": booking.status,
        }
    except BookingConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": str(e), "alternative_slots": e.alternative_slots},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error creating booking: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error creating booking.")


@router.get("/{booking_id}")
async def get_booking_endpoint(booking_id: str, db: Session = Depends(get_db)):
    """Get booking details by booking_id (e.g. BK-XXXXXX)."""
    booking_id = booking_id.strip().upper()
    try:
        booking = service.get_booking(db, booking_id)
        return {
            "booking_id": booking.booking_id,
            "user_id": booking.user_id,
            "property_id": str(booking.property_id),
            "user_email": booking.user_email,
            "visit_date": str(booking.visit_date),
            "visit_time": str(booking.visit_time),
            "status": booking.status,
        }
    except BookingNotFoundError:
        raise HTTPException(status_code=404, detail="Booking not found.")


@router.patch("/{booking_id}")
async def reschedule_booking_endpoint(
    booking_id: str, payload: RescheduleBookingRequest, db: Session = Depends(get_db)
):
    """Reschedule a booking to a new date/time while preserving the booking_id."""
    booking_id = booking_id.strip().upper()
    try:
        booking = service.reschedule_booking(
            db, booking_id, payload.visit_date, payload.visit_time
        )
        return {
            "booking_id": booking.booking_id,
            "visit_date": str(booking.visit_date),
            "visit_time": str(booking.visit_time),
            "status": booking.status,
        }
    except BookingConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": str(e), "alternative_slots": e.alternative_slots},
        )
    except BookingNotFoundError:
        raise HTTPException(status_code=404, detail="Booking not found.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{booking_id}")
async def cancel_booking_endpoint(booking_id: str, db: Session = Depends(get_db)):
    """Cancel a booking — sets status to 'cancelled'."""
    booking_id = booking_id.strip().upper()
    try:
        booking = service.cancel_booking(db, booking_id)
        return {"booking_id": booking.booking_id, "status": booking.status}
    except BookingNotFoundError:
        raise HTTPException(status_code=404, detail="Booking not found.")
