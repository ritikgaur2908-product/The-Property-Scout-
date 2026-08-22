from typing import List, Dict, Any

def get_tools() -> List[Dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "search_properties",
                "description": "Searches the database for properties matching the user's updated preferences. Call this whenever the user updates their budget, locality, BHK, or other preferences, or asks to see properties.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "max_budget": {"type": "integer", "description": "Maximum budget in INR."},
                        "min_bhk": {"type": "integer", "description": "Minimum number of bedrooms (BHK)."},
                        "localities": {"type": "array", "items": {"type": "string"}, "description": "List of neighborhoods."},
                        "accommodation_type": {"type": "string", "enum": ["whole_flat", "room_in_flat"], "description": "Type of accommodation."},
                        "gender": {"type": "string", "enum": ["male", "female", "any"], "description": "Gender preference for flatmates."},
                        "food": {"type": "string", "enum": ["veg", "non_veg", "any"], "description": "Food preference."},
                        "smoking": {"type": "string", "enum": ["smoker", "non_smoker", "any"], "description": "Smoking preference."},
                        "parking": {"type": "boolean", "description": "Whether parking is required."}
                    },
                    "required": ["localities", "max_budget"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_amenities",
                "description": "Fetches nearby amenities (hospitals, supermarkets, gyms, metro stations) for a specific property. Call this when the user asks about what's around a specific property.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "property_id": {
                            "type": "string",
                            "description": "The UUID of the property to check amenities for."
                        }
                    },
                    "required": ["property_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_neighborhood_info",
                "description": "Retrieves real RAG insights about a specific Bengaluru neighborhood (e.g., safety, noise, culture, transport). Call this when the user asks about the vibe or safety of an area.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "locality": {
                            "type": "string",
                            "description": "The name of the neighborhood (e.g. 'Indiranagar', 'Whitefield')."
                        },
                        "topic": {
                            "type": "string",
                            "enum": ["safety", "daily_life", "transport", "culture", "general"],
                            "description": "The specific topic the user is asking about."
                        }
                    },
                    "required": ["locality", "topic"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "book_visit",
                "description": "Initiates a booking request for a property visit.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "property_id": {
                            "type": "string",
                            "description": "The UUID of the property to book."
                        },
                        "date": {
                            "type": "string",
                            "description": "The requested date. (Do not ask the user for 'YYYY-MM-DD' format, just ask them what date they prefer)"
                        },
                        "time": {
                            "type": "string",
                            "description": "The requested time. (Do not ask the user for 'HH:MM' format, just ask them what time they prefer)"
                        },
                        "email": {
                            "type": "string",
                            "description": "The user's email address for confirmation."
                        }
                    },
                    "required": ["property_id", "date", "time", "email"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "send_shortlist_email",
                "description": "Sends the currently shortlisted properties to the user's email.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "email": {
                            "type": "string",
                            "description": "The user's email address."
                        }
                    },
                    "required": ["email"]
                }
            }
        }
    ]
