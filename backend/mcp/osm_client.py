import requests
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

OVERPASS_URL = "http://overpass-api.de/api/interpreter"

def get_amenities(lat: float, lon: float, radius: int = 1500) -> Dict[str, Any]:
    """
    Queries the OpenStreetMap Overpass API for amenities around a specific location.
    
    Args:
        lat: Latitude of the center point.
        lon: Longitude of the center point.
        radius: Search radius in meters (default 1500m / 1.5km).
        
    Returns:
        A dictionary containing the raw Overpass JSON response.
    """
    # Overpass QL query to find various nodes (amenities, leisure, public transport)
    # around the given lat, lon, radius
    overpass_query = f"""
    [out:json][timeout:25];
    (
      node["amenity"~"hospital|clinic|school|college|marketplace|cafe|restaurant"](around:{radius},{lat},{lon});
      node["leisure"~"park|playground"](around:{radius},{lat},{lon});
      node["public_transport"~"station"](around:{radius},{lat},{lon});
      node["shop"~"supermarket|mall"](around:{radius},{lat},{lon});
    );
    out body;
    >;
    out skel qt;
    """
    
    logger.info(f"Querying Overpass API for amenities around {lat}, {lon} within {radius}m...")
    
    headers = {
        "User-Agent": "ThePropertyScout/1.0 (contact@thepropertyscout.com)",
        "Accept": "application/json"
    }
    try:
        response = requests.post(OVERPASS_URL, data={'data': overpass_query}, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Successfully retrieved {len(data.get('elements', []))} elements from OSM.")
        return data
    except Exception as e:
        logger.error(f"Failed to fetch data from Overpass API: {e}")
        return {"elements": []}
