from typing import TypedDict, Optional, List, Dict, Any
import copy
import logging

logger = logging.getLogger(__name__)

# Common speech-to-text / typo variants → canonical Bengaluru locality names
LOCALITY_ALIASES = {
    "core mangla": "Koramangala",
    "core mangala": "Koramangala",
    "kora mangala": "Koramangala",
    "koramangla": "Koramangala",
    "koramangala": "Koramangala",
    "hsr": "HSR Layout",
    "hsr layout": "HSR Layout",
    "indira nagar": "Indiranagar",
    "indiranagar": "Indiranagar",
    "white field": "Whitefield",
    "whitefield": "Whitefield",
    "jayanagar": "Jayanagar",
    "jaya nagar": "Jayanagar",
    "btm": "BTM Layout",
    "btm layout": "BTM Layout",
}


def normalize_locality(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        return cleaned
    alias = LOCALITY_ALIASES.get(cleaned.lower())
    return alias if alias else cleaned


class UserPreferences(TypedDict, total=False):
    max_budget: Optional[int]
    min_bhk: Optional[int]
    localities: Optional[List[str]]
    accommodation_type: Optional[str]  # whole_flat, room_in_flat
    gender: Optional[str]  # male, female, any
    food: Optional[str]
    smoking: Optional[str]
    parking: Optional[bool]
    
class ConversationState:
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id
        self.preferences: UserPreferences = {}
        self.shortlist: List[Dict[str, Any]] = []
        self.history: List[Dict[str, str]] = [] # list of {"role": "user"/"assistant", "content": "..."}
        self.user_email: Optional[str] = None

    def update_preferences(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Updates the internal preferences with only the provided keys.
        Untouched keys remain as is. Returns a dict of what actually changed.
        """
        changes = {}
        for key, value in updates.items():
            if key == "localities" and isinstance(value, list):
                value = [normalize_locality(loc) for loc in value if loc]
            elif key == "locality" and isinstance(value, str):
                value = normalize_locality(value)
                key = "localities"
                existing = self.preferences.get("localities") or []
                if value and value not in existing:
                    value = existing + [value]
                else:
                    value = existing

            if value is not None and self.preferences.get(key) != value:
                changes[key] = value
                self.preferences[key] = value
        
        if changes:
            logger.info(f"Preferences updated: {changes}")
            
        return changes
        
    def add_message(self, role: str, content: str):
        self.history.append({"role": role, "content": content})
