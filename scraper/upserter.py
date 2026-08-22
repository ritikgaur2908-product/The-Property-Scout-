import sys
import logging
from typing import List, Dict
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import text

# Ensure backend modules can be imported
sys.path.append('.')
sys.path.append('./backend')
from backend.db.connection import SessionLocal
from backend.db.models import Property

logger = logging.getLogger(__name__)

def upsert_properties(properties_data: List[Dict]):
    """
    Takes a list of property dictionaries and upserts them into the database
    using PostgreSQL native multi-row ON CONFLICT DO UPDATE in chunks of 500.
    Executes in ~1-2 seconds with live chunk progress logs.
    """
    db = SessionLocal()
    try:
        if not properties_data:
            logger.info("No properties to upsert.")
            return

        valid_props = [p for p in properties_data if p.get("source_id")]
        total_valid = len(valid_props)
        chunk_size = 500
        total_chunks = (total_valid - 1) // chunk_size + 1

        logger.info(f"Starting native PostgreSQL bulk upsert for {total_valid} properties in {total_chunks} chunks...")

        for i in range(0, total_valid, chunk_size):
            chunk = valid_props[i:i + chunk_size]
            stmt = pg_insert(Property).values(chunk)
            stmt = stmt.on_conflict_do_update(
                index_elements=["source_id"],
                set_={
                    "rent": stmt.excluded.rent,
                    "rooms": stmt.excluded.rooms,
                    "accommodation_type": stmt.excluded.accommodation_type,
                    "gender_openness": stmt.excluded.gender_openness,
                    "flatmate_food_pref": stmt.excluded.flatmate_food_pref,
                    "flatmate_smoking_pref": stmt.excluded.flatmate_smoking_pref,
                    "address": stmt.excluded.address,
                    "locality": stmt.excluded.locality,
                    "latitude": stmt.excluded.latitude,
                    "longitude": stmt.excluded.longitude,
                    "source_url": stmt.excluded.source_url,
                    "status": "available",
                    "updated_at": text("NOW()"),
                }
            )
            db.execute(stmt)
            db.commit()
            logger.info(f"Progress: Upserted chunk {i // chunk_size + 1}/{total_chunks} ({min(i + chunk_size, total_valid)}/{total_valid} properties)")

        logger.info(f"Successfully finished native bulk upsert of {total_valid} properties.")

    except Exception as e:
        db.rollback()
        logger.error(f"Error during upsert: {str(e)}")
        raise
    finally:
        db.close()
