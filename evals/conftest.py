"""
evals/conftest.py — Pytest fixtures for the evaluation suite.

Key design decisions:
  • Uses SQLite in-memory for the test DB (no PostgreSQL needed).
  • JSONB columns in models.py are PostgreSQL-only, so we import models
    AFTER monkey-patching the dialect column type to plain JSON for tests.
  • Property seeds use the EXACT column names from models.py:
    source_id, rooms, accommodation_type, gender_openness, flatmate_food_pref,
    parking_available, parking_count, address, locality, status.
  • The `id` primary key is a UUID(as_uuid=True) — we let SQLAlchemy generate it
    automatically (default=uuid.uuid4) rather than passing a string.
"""
import json
import os
import uuid
from datetime import date, time, datetime
from typing import Any, Dict, List

import pytest
from sqlalchemy import create_engine, JSON
from sqlalchemy.orm import sessionmaker

# ── SQLite compatibility patch ────────────────────────────────────────────────
# models.py uses JSONB (PostgreSQL-only). We swap it for plain JSON before
# any model is imported so SQLite can handle the schema.
import sqlalchemy.dialects.postgresql as _pg_dialect
_pg_dialect.JSONB = JSON  # type: ignore[attr-defined]

from backend.db.connection import Base  # noqa: E402 — must come after patch
import backend.db.models  # noqa: E402 — register all models on Base

from backend.db.models import Property, Booking, Session as DbSession  # noqa: E402

# ─────────────────────────────────────────────────────────────────────────────
# In-memory SQLite engine — isolated per test module
# ─────────────────────────────────────────────────────────────────────────────
_SQLITE_URL = "sqlite:///:memory:"

_engine = create_engine(
    _SQLITE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def mock_db():
    """
    Creates the full schema in SQLite, seeds realistic Property rows that match
    the actual models.py column names, yields the session, then tears down.
    """
    Base.metadata.create_all(bind=_engine)
    db = TestingSessionLocal()

    # ── Seed Properties ──────────────────────────────────────────────────────
    props = [
        Property(
            source_id="PROP-TEST-001",
            accommodation_type="whole_flat",
            rent=42000,
            rooms=2,
            move_in_time="Immediate",
            gender_openness="any",
            parking_available=False,
            parking_count=0,
            flatmate_food_pref=None,
            flatmate_smoking_pref=None,
            address="12, 100ft Road, Indiranagar",
            locality="Indiranagar",
            source_url="https://bengaluru.rent/prop-001",
            status="available",
            scraped_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ),
        Property(
            source_id="PROP-TEST-002",
            accommodation_type="whole_flat",
            rent=62000,
            rooms=3,
            move_in_time="15 days",
            gender_openness="any",
            parking_available=True,
            parking_count=1,
            flatmate_food_pref=None,
            flatmate_smoking_pref=None,
            address="88, Outer Ring Road, Bellandur",
            locality="Bellandur",
            source_url="https://bengaluru.rent/prop-002",
            status="available",
            scraped_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ),
        Property(
            source_id="PROP-TEST-003",
            accommodation_type="room_in_flat",
            rent=14500,
            rooms=3,
            move_in_time="Immediate",
            gender_openness="male",
            parking_available=False,
            parking_count=0,
            flatmate_food_pref="veg",
            flatmate_smoking_pref="non_smoker",
            address="27th Main, HSR Layout Sector 2",
            locality="HSR Layout",
            source_url="https://bengaluru.rent/prop-003",
            status="available",
            scraped_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ),
        Property(
            source_id="PROP-TEST-004",
            accommodation_type="whole_flat",
            rent=48000,
            rooms=2,
            move_in_time="1 month",
            gender_openness="any",
            parking_available=True,
            parking_count=2,
            flatmate_food_pref=None,
            flatmate_smoking_pref=None,
            address="80ft Road, Koramangala Block 4",
            locality="Koramangala",
            source_url="https://bengaluru.rent/prop-004",
            status="available",
            scraped_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ),
        Property(
            source_id="PROP-TEST-005",
            accommodation_type="whole_flat",
            rent=75000,
            rooms=3,
            move_in_time="Immediate",
            gender_openness="any",
            parking_available=True,
            parking_count=2,
            flatmate_food_pref=None,
            flatmate_smoking_pref=None,
            address="ITPL Main Road, Whitefield",
            locality="Whitefield",
            source_url="https://bengaluru.rent/prop-005",
            status="available",
            scraped_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ),
        Property(
            source_id="PROP-TEST-006",
            accommodation_type="room_in_flat",
            rent=11000,
            rooms=2,
            move_in_time="Immediate",
            gender_openness="female",
            parking_available=False,
            parking_count=0,
            flatmate_food_pref="veg",
            flatmate_smoking_pref="non_smoker",
            address="BTM Layout 2nd Stage",
            locality="BTM Layout",
            source_url="https://bengaluru.rent/prop-006",
            status="available",
            scraped_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ),
        # Unavailable property — must NOT appear in valid IDs for grounding checks
        Property(
            source_id="PROP-TEST-SOLD",
            accommodation_type="whole_flat",
            rent=35000,
            rooms=2,
            move_in_time="N/A",
            gender_openness="any",
            parking_available=False,
            parking_count=0,
            address="Old Airport Road, Indiranagar",
            locality="Indiranagar",
            source_url="https://bengaluru.rent/prop-sold",
            status="unavailable",
            scraped_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ),
    ]
    db.add_all(props)
    db.commit()

    yield db

    db.close()
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture(scope="module")
def valid_property_ids(mock_db) -> set:
    """
    Returns the set of source_ids for all properties with status='available'.
    Used by grounding checks to validate property IDs mentioned in bot responses.
    """
    available = mock_db.query(Property).filter(Property.status == "available").all()
    return {p.source_id for p in available}


@pytest.fixture
def mock_rag_chunks() -> Dict[str, List[str]]:
    """
    Realistic RAG chunks keyed by locality name.
    Mirrors the structure used by synthesizer.py / retriever.py.
    Each value is a list of text snippets the LLM would receive as context.
    """
    return {
        "Indiranagar": [
            "Resident observation in Indiranagar: \"Indiranagar 100ft road is the party capital. "
            "If you live 1-2 streets behind it, prepare for loud bass until 1 AM on weekends.\"",
            "Resident feedback for Indiranagar (Overall Sentiment: Positive, based on 342 discussions): "
            "Highly walkable, excellent metro connectivity via Swami Vivekananda Metro station. "
            "Chain snatching incidents have been reported early in the mornings near quieter streets.",
            "Resident observation in Indiranagar: \"Bescom power cuts are frequent — 1-2 hours per week. "
            "An inverter is mandatory if you work from home.\"",
        ],
        "HSR Layout": [
            "Resident feedback for HSR Layout: Well-planned wide roads and tree-lined avenues. "
            "Quieter, more family-oriented vibe. No direct metro — nearest is Silk Board which has severe traffic.",
            "Resident observation in HSR Layout: \"Walkability on 27th main is excellent — footpaths actually usable. "
            "But Sector 1 garbage management is occasionally poor.\"",
            "Resident observation in HSR Layout: \"Very safe, well-lit streets. Strict 11 PM noise curfew "
            "in residential societies.\"",
        ],
        "Koramangala": [
            "Resident observation in Koramangala: \"Block 4 traffic on 80ft road is insane. "
            "A 2km commute takes 30 mins in the evening.\"",
            "Resident feedback for Koramangala: Startup and student-heavy vibe, vibrant nightlife. "
            "No metro station nearby — rely on autos or own vehicle. Parking on the street leads to frequent towing.",
            "Resident observation in Koramangala: \"Stray dog menace at night near parks. "
            "Dogs bark constantly past midnight.\"",
        ],
        "Whitefield": [
            "Resident observation in Whitefield: \"The new purple line metro has improved connectivity. "
            "But internal roads near tech parks are dusty, pothole-ridden and jam-prone.\"",
            "Resident feedback for Whitefield: Mostly gated communities — very safe and insulated. "
            "Water supply is a critical issue. Most apartments rely 100% on private water tankers.",
            "Resident observation in Whitefield: \"Air quality is bad due to ongoing construction. "
            "Dust is terrible on balconies facing the main road.\"",
        ],
        "Bellandur": [
            "Resident observation in Bellandur: \"Major waterlogging during monsoon — the lake flooding "
            "makes entire stretches of road impassable for 2-3 days.\"",
            "Resident feedback for Bellandur: Growing tech corridor with many new apartments. "
            "Traffic towards Outer Ring Road in the morning can add 30-45 minutes.",
        ],
        "BTM Layout": [
            "Resident observation in BTM Layout: \"Reasonably priced and well-connected to Silk Board. "
            "But auto drivers are notorious for refusing rides during peak hours.\"",
            "Resident feedback for BTM Layout: Mix of students and young professionals. "
            "Vegetarian food options are plentiful. Noise levels moderate — not as loud as Koramangala.",
        ],
    }


@pytest.fixture(scope="module")
def golden_dataset() -> List[Dict[str, Any]]:
    """
    Loads the full golden dataset from evals/golden_dataset.json.
    This is the single source of truth for all test cases.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    dataset_path = os.path.join(here, "golden_dataset.json")
    with open(dataset_path, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture
def test_session_factory():
    """
    Returns a factory that creates fresh SQLite sessions for tests
    that need to manipulate DB state without affecting mock_db.
    """
    engine = create_engine(_SQLITE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    yield SessionFactory

    Base.metadata.drop_all(bind=engine)
