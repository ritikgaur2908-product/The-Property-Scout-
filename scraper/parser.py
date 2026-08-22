import json
import re
import requests
import logging

logger = logging.getLogger(__name__)

class BengaluruRentParser:
    def __init__(self, url="https://bengaluru.rent/"):
        self.url = url
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    def fetch_data(self):
        """
        Fetches the HTML, extracts Supabase credentials, and queries the Supabase Edge Function directly.
        """
        logger.info(f"Fetching {self.url} ...")
        resp = requests.get(self.url, headers=self.headers, timeout=15)
        resp.raise_for_status()
        html = resp.text
        
        # 1. Extract Supabase URL from the page source
        supabase_url_match = re.search(r"const\s+SUPABASE_URL\s*=\s*'([^']+)'", html)
        
        pins_data = []
        tolet_data = [] # The edge function seems to return all pins in one array
        
        if supabase_url_match:
            supabase_url = supabase_url_match.group(1)
            logger.info("Found Supabase URL. Querying Edge Function directly...")
            
            # Query pins via edge function (no auth required in client script)
            try:
                pins_resp = requests.get(f"{supabase_url}/functions/v1/get-pins", timeout=15)
                pins_resp.raise_for_status()
                json_data = pins_resp.json()
                pins_data = json_data.get('pins', [])
                logger.info(f"Successfully fetched {len(pins_data)} pins from Edge Function.")
            except Exception as e:
                logger.warning(f"Failed to fetch pins from Edge Function: {e}")
                
        else:
            logger.warning("Could not find Supabase URL in HTML.")
            
        return pins_data, tolet_data
        
    def parse_properties(self, pins_data, tolet_data):
        properties = []
        all_spots = pins_data + tolet_data
        
        for item in all_spots:
            if str(item.get("status", "")).lower() == "not for rent":
                continue
                
            prop = {
                "source_id": str(item.get("id", item.get("source_id", ""))),
                "accommodation_type": item.get("listing_type") or "whole_flat",
                "rent": str(item.get("rent_amount", "0")),
                "rooms": str(item.get("bhk", "0")),
                "move_in_time": str(item.get("available_from", "")),
                "gender_openness": item.get("pref_gender", "any"),
                "parking_available": item.get("parking", False),
                "parking_count": item.get("parking_count", 0),
                "flatmate_food_pref": item.get("pref_food", "any"),
                "flatmate_smoking_pref": item.get("pref_smoking", "any"),
                "address": item.get("society") or "Unknown",
                "locality": item.get("area", ""),
                "latitude": item.get("lat", None),
                "longitude": item.get("lng", None),
                "source_url": self.url,
                "raw_description": item.get("feedback", "")
            }
            
            properties.append(prop)
            
        return properties
