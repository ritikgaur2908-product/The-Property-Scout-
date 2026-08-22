import sys
import logging

# Ensure backend modules can be imported
sys.path.append('.')
sys.path.append('./backend')

from scraper.parser import BengaluruRentParser
from scraper.pii_scrubber import scrub_pii
from scraper.normalizer import (
    normalize_rent, normalize_bhk, normalize_gender, 
    normalize_food_pref, normalize_smoking_pref
)
from scraper.geocoder import NominatimGeocoder
from scraper.upserter import upsert_properties

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_scraper():
    logger.info("Starting Property Scraper...")
    
    # 1. Fetch and Parse Data
    parser = BengaluruRentParser()
    pins_data, tolet_data = parser.fetch_data()
    raw_properties = parser.parse_properties(pins_data, tolet_data)
    
    logger.info(f"Extracted {len(raw_properties)} properties from source.")
    
    # 2. Geocoder Setup
    geocoder = NominatimGeocoder()
    
    cleaned_properties = []
    
    # 3. Clean, Normalize, and Geocode
    for prop in raw_properties:
        # Scrub PII from description and address
        raw_desc = prop.get("raw_description", "")
        if raw_desc:
            prop["raw_description"] = scrub_pii(raw_desc)
            
        address = prop.get("address", "")
        if address:
            prop["address"] = scrub_pii(address)
            
        # Normalize fields
        prop["rent"] = normalize_rent(prop.get("rent", ""))
        prop["rooms"] = normalize_bhk(prop.get("rooms", ""))
        prop["gender_openness"] = normalize_gender(prop.get("gender_openness", ""))
        prop["flatmate_food_pref"] = normalize_food_pref(prop.get("flatmate_food_pref", ""))
        prop["flatmate_smoking_pref"] = normalize_smoking_pref(prop.get("flatmate_smoking_pref", ""))
        
        # Geocoding if coordinates are missing
        if not prop.get("latitude") or not prop.get("longitude"):
            if address:
                coords = geocoder.geocode(address)
                if coords:
                    prop["latitude"], prop["longitude"] = coords
        
        # We don't store raw_description in DB directly based on current schema, 
        # but if we did, we'd assign it here. (Skipping for now to match schema).
        if "raw_description" in prop:
            del prop["raw_description"]
            
        cleaned_properties.append(prop)
        
    logger.info(f"Finished cleaning {len(cleaned_properties)} properties.")
    
    # 4. Upsert to Database
    if cleaned_properties:
        upsert_properties(cleaned_properties)
    else:
        logger.info("No properties to upsert.")
        
    logger.info("Scraping completed successfully.")

if __name__ == "__main__":
    run_scraper()
