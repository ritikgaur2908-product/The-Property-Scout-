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
    Optimized with batch lookups (chunks of 1,000) so large datasets process in seconds.
    """
    db = SessionLocal()
    try:
        scraped_source_ids = [str(p['source_id']) for p in properties_data if 'source_id' in p]
        
        # 1. Batch lookup existing properties in chunks of 1,000 to avoid N+1 queries
        existing_props = {}
        chunk_size = 1000
        for i in range(0, len(scraped_source_ids), chunk_size):
            chunk = scraped_source_ids[i:i + chunk_size]
            results = db.query(Property).filter(Property.source_id.in_(chunk)).all()
            for p in results:
                existing_props[p.source_id] = p

        upserted_count = 0
        new_count = 0
        
        # 2. Process updates and new additions in-memory
        for data in properties_data:
            source_id = str(data.get('source_id'))
            if not source_id:
                continue
                
            if source_id in existing_props:
                existing = existing_props[source_id]
                for key, value in data.items():
                    setattr(existing, key, value)
                existing.status = 'available'
                upserted_count += 1
            else:
                new_prop = Property(**data)
                new_prop.status = 'available'
                db.add(new_prop)
                new_count += 1
                
        # 3. Mark old properties not in this batch as unavailable
        if scraped_source_ids:
            for i in range(0, len(scraped_source_ids), chunk_size):
                chunk = scraped_source_ids[i:i + chunk_size]
                db.query(Property).filter(
                    Property.source_id.notin_(chunk),
                    Property.status == 'available'
                ).update({"status": "unavailable"}, synchronize_session=False)

        db.commit()
        logger.info(f"Successfully upserted: {upserted_count} updated, {new_count} inserted in bulk.")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error during upsert: {str(e)}")
        raise
    finally:
        db.close()
