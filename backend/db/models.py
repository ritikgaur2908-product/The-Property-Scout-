import uuid
from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    Text,
    Numeric,
    DateTime,
    Date,
    Time,
    ForeignKey,
    UniqueConstraint,
    text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from backend.db.connection import Base

class Property(Base):
    __tablename__ = "properties"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    source_id = Column(String(255), unique=True, nullable=False)
    accommodation_type = Column(String(50), nullable=False)  # 'whole_flat' | 'room_in_flat'
    rent = Column(Integer, nullable=False)
    rooms = Column(Integer, nullable=False)  # BHK count
    move_in_time = Column(String(100), nullable=True)
    gender_openness = Column(String(50), nullable=True)  # 'male' | 'female' | 'any'
    parking_available = Column(Boolean, default=False, server_default=text("false"))
    parking_count = Column(Integer, default=0, server_default=text("0"))
    flatmate_food_pref = Column(String(50), nullable=True)  # 'veg' | 'non_veg' | 'any'
    flatmate_smoking_pref = Column(String(50), nullable=True)  # 'smoker' | 'non_smoker' | 'any'
    address = Column(Text, nullable=False)
    locality = Column(String(255), nullable=True, index=True)
    latitude = Column(Numeric(10, 8), nullable=True)
    longitude = Column(Numeric(11, 8), nullable=True)
    source_url = Column(Text, nullable=True)
    status = Column(String(20), default="available", server_default="available", index=True)
    scraped_at = Column(DateTime, nullable=False, server_default=text("NOW()"))
    created_at = Column(DateTime, nullable=False, server_default=text("NOW()"))
    updated_at = Column(DateTime, nullable=False, server_default=text("NOW()"), onupdate=text("NOW()"))

    # Relationships
    amenities = relationship("Amenity", back_populates="property", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="property")


class Amenity(Base):
    __tablename__ = "amenities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)  # 'daily_essentials', 'health_education', etc.
    name = Column(String(255), nullable=False)
    type = Column(String(100), nullable=True)  # e.g., 'pharmacy', 'metro_station'
    distance_meters = Column(Integer, nullable=True)
    latitude = Column(Numeric(10, 8), nullable=True)
    longitude = Column(Numeric(11, 8), nullable=True)
    fetched_at = Column(DateTime, nullable=False, server_default=text("NOW()"))

    # Relationships
    property = relationship("Property", back_populates="amenities")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    booking_id = Column(String(20), unique=True, nullable=False, index=True)  # BK-XXXXXX
    user_id = Column(String(20), nullable=False, index=True)  # USR-XXXXXX
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id"), nullable=False, index=True)
    user_email = Column(String(255), nullable=False)
    visit_date = Column(Date, nullable=False)
    visit_time = Column(Time, nullable=False)
    status = Column(String(20), default="confirmed", server_default="confirmed", index=True)  # 'confirmed', 'cancelled', 'rescheduled'
    created_at = Column(DateTime, nullable=False, server_default=text("NOW()"))
    updated_at = Column(DateTime, nullable=False, server_default=text("NOW()"), onupdate=text("NOW()"))

    # Relationships
    property = relationship("Property", back_populates="bookings")

    # Prevent double-booking: one property, one date+time slot
    __table_args__ = (
        UniqueConstraint("property_id", "visit_date", "visit_time", name="unique_property_slot"),
    )


class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    user_id = Column(String(20), nullable=True)
    preferences = Column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    shortlist = Column(JSONB, default=list, server_default=text("'[]'::jsonb"))
    transcript = Column(JSONB, default=list, server_default=text("'[]'::jsonb"))
    status = Column(String(20), default="active", server_default="active")
    created_at = Column(DateTime, nullable=False, server_default=text("NOW()"))
    updated_at = Column(DateTime, nullable=False, server_default=text("NOW()"), onupdate=text("NOW()"))
