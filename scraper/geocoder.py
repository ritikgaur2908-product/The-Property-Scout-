import time
import logging
from typing import Tuple, Optional
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

logger = logging.getLogger(__name__)

class NominatimGeocoder:
    def __init__(self, user_agent: str = "property_scout_scraper_1.0"):
        self.geolocator = Nominatim(user_agent=user_agent)
        self.last_request_time = 0.0
        self.delay = 1.1 # strict 1 req/sec policy + 0.1s buffer

    def _wait(self):
        elapsed = time.time() - self.last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)

    def geocode(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Geocodes a text address to (latitude, longitude).
        Returns None if not found or on error.
        """
        if not address:
            return None
            
        # Append city and country for better accuracy if not present
        if "bengaluru" not in address.lower() and "bangalore" not in address.lower():
            address = f"{address}, Bengaluru, Karnataka, India"
            
        self._wait()
        
        try:
            location = self.geolocator.geocode(address, timeout=10)
            self.last_request_time = time.time()
            if location:
                return (location.latitude, location.longitude)
            else:
                logger.warning(f"Could not geocode address: {address}")
                return None
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            logger.error(f"Geocoding error for {address}: {str(e)}")
            self.last_request_time = time.time()
            return None
