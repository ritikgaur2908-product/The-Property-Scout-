from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
import uuid

from backend.llm.state_manager import ConversationState
from backend.llm.orchestrator import Orchestrator
from backend.db.connection import SessionLocal
from backend.db.queries import search_properties_in_db
from backend.api.middleware.validation import MessageRequest, RemoveFilterRequest

router = APIRouter()

# In-memory store for sessions (for development). In prod, store in Redis or DB.
SESSIONS: Dict[str, ConversationState] = {}
orchestrator = Orchestrator()

def _apply_filter_removal(state: ConversationState, key: str, value: Optional[str] = None) -> None:
    prefs = state.preferences

    if key == "locality" and value:
        localities = prefs.get("localities") or []
        prefs["localities"] = [loc for loc in localities if loc != value]
        if not prefs["localities"]:
            prefs.pop("localities", None)
    elif key == "localities":
        prefs.pop("localities", None)
    elif key == "max_budget":
        prefs.pop("max_budget", None)
    elif key == "min_bhk":
        prefs.pop("min_bhk", None)
    elif key == "accommodation_type":
        prefs.pop("accommodation_type", None)
    elif key == "parking":
        prefs.pop("parking", None)
    elif key == "gender":
        prefs.pop("gender", None)
    else:
        prefs.pop(key, None)

def _refresh_shortlist(state: ConversationState) -> None:
    db = SessionLocal()
    try:
        properties, _ = search_properties_in_db(db, state.preferences)
        state.shortlist = properties
    finally:
        db.close()

@router.post("")
@router.post("/")
def create_session():
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = ConversationState()
    return {"session_id": session_id}

@router.get("/{session_id}")
def get_session(session_id: str):
    if session_id not in SESSIONS:
        SESSIONS[session_id] = ConversationState()
    state = SESSIONS[session_id]
    return {
        "session_id": session_id,
        "preferences": state.preferences,
        "shortlist": state.shortlist,
        "history": state.history,
        "user_email": state.user_email,
    }

@router.post("/{session_id}/message")
async def send_message(session_id: str, payload: MessageRequest):
    if session_id not in SESSIONS:
        SESSIONS[session_id] = ConversationState()
        
    state = SESSIONS[session_id]
    response_text = await orchestrator.process_message(state, payload.message)
    
    return {
        "response": response_text,
        "preferences": state.preferences,
        "shortlist": state.shortlist,
        "user_email": state.user_email,
    }

@router.post("/{session_id}/remove-filter")
async def remove_filter(session_id: str, payload: RemoveFilterRequest):
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")

    state = SESSIONS[session_id]
    _apply_filter_removal(state, payload.key, payload.value)
    _refresh_shortlist(state)

    return {
        "preferences": state.preferences,
        "shortlist": state.shortlist,
    }
