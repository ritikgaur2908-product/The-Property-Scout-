"""
backend/api/middleware/validation.py

Pydantic request schemas for all API route bodies.

These schemas are used in two ways:
  1. As FastAPI endpoint parameter types — FastAPI will auto-validate and
     return 422 Unprocessable Entity with a detailed error body.
  2. As documentation — FastAPI auto-generates OpenAPI schema from them.

Design decisions:
  • All string fields strip whitespace on validation (via @field_validator).
  • UUIDs are validated as strings to remain compatible with the existing
    service layer (which accepts str and converts internally).
  • Dates and times are accepted as strings in the formats the LLM produces
    (e.g. "2026-08-25", "10:30 AM") — the booking service normalises them.
  • Email validation uses Pydantic's built-in EmailStr format.
"""
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


# ─────────────────────────────────────────────────────────────────────────────
# Session routes  (/api/session/...)
# ─────────────────────────────────────────────────────────────────────────────

class MessageRequest(BaseModel):
    """POST /api/session/{session_id}/message"""
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The user's text message to the bot.",
        examples=["I'm looking for a 2BHK in Indiranagar under 45k."],
    )

    @field_validator("message")
    @classmethod
    def strip_message(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Message must not be empty or whitespace.")
        return stripped


class RemoveFilterRequest(BaseModel):
    """POST /api/session/{session_id}/remove-filter"""
    key: str = Field(
        ...,
        description="The preference key to remove (e.g. 'max_budget', 'localities').",
        examples=["max_budget"],
    )
    value: Optional[str] = Field(
        default=None,
        description="For list-type keys (e.g. 'localities'), the specific value to remove.",
        examples=["Indiranagar"],
    )

    @field_validator("key")
    @classmethod
    def validate_key(cls, v: str) -> str:
        v = v.strip()
        allowed_keys = {
            "max_budget", "min_bhk", "localities", "locality",
            "accommodation_type", "gender", "food", "smoking", "parking",
        }
        if v not in allowed_keys:
            raise ValueError(
                f"Unknown filter key '{v}'. Allowed keys: {sorted(allowed_keys)}"
            )
        return v


# ─────────────────────────────────────────────────────────────────────────────
# Booking routes  (/api/bookings/...)
# ─────────────────────────────────────────────────────────────────────────────

class CreateBookingRequest(BaseModel):
    """POST /api/bookings"""
    property_id: str = Field(
        ...,
        min_length=1,
        description="UUID of the property to book.",
    )
    email: EmailStr = Field(
        ...,
        description="User's email address for booking confirmation.",
        examples=["user@example.com"],
    )
    visit_date: str = Field(
        ...,
        description="Requested visit date (e.g. '2026-08-25' or 'tomorrow').",
        examples=["2026-08-25"],
    )
    visit_time: str = Field(
        ...,
        description="Requested visit time (e.g. '10:00 AM' or '14:30').",
        examples=["10:00 AM"],
    )

    @field_validator("property_id")
    @classmethod
    def strip_property_id(cls, v: str) -> str:
        return v.strip()

    @field_validator("visit_date", "visit_time")
    @classmethod
    def strip_datetime(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Date/time fields must not be empty.")
        return v


class RescheduleBookingRequest(BaseModel):
    """PATCH /api/bookings/{booking_id}"""
    visit_date: str = Field(
        ...,
        description="New visit date.",
        examples=["2026-08-30"],
    )
    visit_time: str = Field(
        ...,
        description="New visit time.",
        examples=["3:00 PM"],
    )

    @field_validator("visit_date", "visit_time")
    @classmethod
    def strip_fields(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Date/time fields must not be empty.")
        return v


# ─────────────────────────────────────────────────────────────────────────────
# Notification routes  (/api/notify/...)
# ─────────────────────────────────────────────────────────────────────────────

class ShortlistEmailRequest(BaseModel):
    """POST /api/notify/shortlist"""
    email: EmailStr = Field(
        ...,
        description="The email address to send the shortlist to.",
        examples=["user@example.com"],
    )
    shortlist: List[dict] = Field(
        default_factory=list,
        description="The list of property objects to include in the email.",
        max_length=20,
    )
