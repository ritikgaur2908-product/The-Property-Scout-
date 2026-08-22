from fastapi import APIRouter
import logging
import uuid

logger = logging.getLogger("routes-properties")
router = APIRouter(prefix="/api/properties", tags=["Properties"])

@router.get("")
async def search_properties(locality: str = None, max_budget: int = None, bhk: int = None):
    """
    Search properties with query params (locality, rent, BHK)
    """
    logger.info(f"Searching properties: locality={locality}, max_budget={max_budget}, bhk={bhk}")
    dummy_id = str(uuid.uuid4())
    return {
        "count": 1,
        "results": [
            {
                "id": dummy_id,
                "source_id": "dummy-src-1",
                "accommodation_type": "whole_flat",
                "rent": 35000,
                "rooms": 2,
                "move_in_time": "Immediately",
                "gender_openness": "any",
                "parking_available": True,
                "parking_count": 1,
                "address": "456, 12th Main Road, Indiranagar, Bengaluru",
                "locality": "Indiranagar",
                "status": "available"
            }
        ]
    }

@router.get("/{property_id}")
async def get_property(property_id: str):
    """
    Get full property details
    """
    logger.info(f"Retrieving property details for: {property_id}")
    return {
        "id": property_id,
        "source_id": "dummy-src-1",
        "accommodation_type": "whole_flat",
        "rent": 35000,
        "rooms": 2,
        "move_in_time": "Immediately",
        "gender_openness": "any",
        "parking_available": True,
        "parking_count": 1,
        "address": "456, 12th Main Road, Indiranagar, Bengaluru",
        "locality": "Indiranagar",
        "status": "available"
    }

@router.get("/{property_id}/amenities")
async def get_property_amenities(property_id: str):
    """
    Get amenities for a specific property
    """
    logger.info(f"Retrieving amenities for property: {property_id}")
    return {
        "property_id": property_id,
        "amenities": [
            {"category": "daily_essentials", "name": "Namdhari's Fresh", "type": "supermarket", "distance_meters": 350},
            {"category": "transport", "name": "Indiranagar Metro Station", "type": "metro_station", "distance_meters": 600},
            {"category": "recreation", "name": "Cult Fit Indiranagar", "type": "gym", "distance_meters": 450}
        ]
    }

@router.get("/{property_id}/neighborhood")
async def get_property_neighborhood(property_id: str):
    """
    Get RAG-sourced neighborhood guidance
    """
    logger.info(f"Retrieving neighborhood insights for property: {property_id}")
    return {
        "property_id": property_id,
        "locality": "Indiranagar",
        "guidance": {
            "safety": "Indiranagar is generally safe, well-lit, and active until 11 PM.",
            "noise": "Traffic noise can be high on 100 Feet Road, but residential streets are quiet.",
            "transit": "Purple line metro makes commuting towards MG Road or Whitefield very fast."
        },
        "sources": [
            {"claim": "Safe, well-lit streets", "source_url": "https://reddit.com/r/bangalore/comments/abc123"}
        ]
    }
