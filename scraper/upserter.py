import sys
import logging
from typing import List, Dict

# Ensure backend modules can be imported
sys.path.append('.')
sys.path.append('./backend')
from backend.db.connection import SessionLocal
from backend.db.models import Property

logger = logging.getLogger(__name__)

def upsert_properties(properties_data: List[Dict]):
    """
    Takes a list of property dictionaries and upserts them into the database.
    Uses source_id to check if property exists.
    Also marks any properties not in the current scraped batch as 'unavailable'.
    """
    db = SessionLocal()
    try:
        # Get all current source_ids in the batch
        scraped_source_ids = [str(p['source_id']) for p in properties_data if 'source_id' in p]
        
        upserted_count = 0
        new_count = 0
        
        for data in properties_data:
            source_id = str(data.get('source_id'))
            if not source_id:
                continue
                
            existing = db.query(Property).filter(Property.source_id == source_id).first()
            if existing:
                # Update existing record
                for key, value in data.items():
                    setattr(existing, key, value)
                existing.status = 'available'
                upserted_count += 1
            else:
                # Insert new record
                new_prop = Property(**data)
                new_prop.status = 'available'
                db.add(new_prop)
                new_count += 1
                
        # Mark properties not found in this run as unavailable
        if scraped_source_ids:
            unavailable_count = db.query(Property).filter(
                Property.source_id.notin_(scraped_source_ids),
                Property.status == 'available'
            ).update({"status": "unavailable"}, synchronize_session=False)
            logger.info(f"Marked {unavailable_count} old properties as unavailable.")
            
        db.commit()
        logger.info(f"Successfully upserted: {upserted_count} updated, {new_count} inserted.")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error during upsert: {str(e)}")
        raise
    finally:
        db.close()
