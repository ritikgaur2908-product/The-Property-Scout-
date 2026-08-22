import asyncio
import json
import logging
import re
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from backend.config import settings
from backend.voice.stt import DeepgramSTT
from backend.voice.tts import IndianTTS
from backend.llm.orchestrator import Orchestrator
from backend.llm.state_manager import ConversationState
from backend.api.routes.session import SESSIONS

logger = logging.getLogger(__name__)
router = APIRouter()

GREETING_TEXT = "Hi! I'm your Property Scout. I'll help you find the perfect rental in Bengaluru. What are you looking for?"

# Pattern for a valid UUID session token
_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE,
)


def _is_valid_token(token: str) -> bool:
    """Returns True if token looks like a UUID."""
    return bool(token and _UUID_RE.match(token.strip()))



async def safe_send_json(websocket: WebSocket, data: dict) -> bool:
    """Send JSON only if the WebSocket is still connected. Returns True on success."""
    try:
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_json(data)
            return True
    except Exception as e:
        logger.warning(f"safe_send_json failed: {e}")
    return False


async def safe_send_bytes(websocket: WebSocket, data: bytes) -> bool:
    """Send bytes only if the WebSocket is still connected. Returns True on success."""
    try:
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_bytes(data)
            return True
    except Exception as e:
        logger.warning(f"safe_send_bytes failed: {e}")
    return False


@router.websocket("/stream")
async def voice_stream(
    websocket: WebSocket,
    session_id: str = "default",
    session_token: str = "",
):
    """
    Handles bidirectional audio and text WebSocket streaming.

    Authentication:
      Clients must supply their session_id as the `session_token` query param
      (i.e. the same UUID returned by POST /api/session).  The server validates
      that it is a well-formed UUID before accepting the connection.
      In DEBUG mode auth is skipped to ease local development.

    Protocol:
      Receives raw audio WAV bytes or JSON text frames from the client.
      Transcribes audio via STT, processes via LLM Orchestrator, synthesizes
      TTS, and streams back text, shortlist, and audio bytes.
    """
    # ── Auth check ─────────────────────────────────────────────────────────
    if not settings.DEBUG:
        token = session_token or session_id or websocket.headers.get("X-Session-Token", "")
        if not token:
            logger.warning("WS rejected — no session_token provided (session=%s)", session_id)
            await websocket.close(code=4001, reason="session_token is required")
            return
        if not _is_valid_token(token):
            logger.warning("WS rejected — invalid session_token format (session=%s)", session_id)
            await websocket.close(code=4003, reason="Invalid session_token")
            return

    await websocket.accept()
    logger.info("Voice WebSocket accepted: session=%s", session_id)

    stt = DeepgramSTT()
    tts = IndianTTS()
    orchestrator = Orchestrator()

    if session_id not in SESSIONS:
        SESSIONS[session_id] = ConversationState(session_id=session_id)
    state = SESSIONS[session_id]

    async def enrich_properties_background(properties):
        from backend.rag.synthesizer import format_insights_for_display
        from backend.mcp.osm_client import get_amenities
        from backend.mcp.amenity_mapper import map_osm_amenities
        from backend.db.connection import SessionLocal
        from backend.db.models import Property

        known_localities = [
            "Koramangala", "Whitefield", "Indiranagar", "HSR Layout", "Jayanagar",
            "BTM Layout", "Marathahalli", "Electronic City", "Bellandur", "Hebbal",
        ]

        def resolve_locality(prop, db_prop):
            if prop.get("locality"):
                return prop["locality"]
            if db_prop and db_prop.locality:
                return str(db_prop.locality)
            address = (prop.get("address") or (db_prop.address if db_prop else "") or "").lower()
            for loc in known_localities:
                if loc.lower() in address:
                    return loc
            return None
        
        loop = asyncio.get_event_loop()
        for prop in properties:
            amenities = []
            db_prop = None
            try:
                db_session = SessionLocal()
                db_prop = db_session.query(Property).filter(Property.id == prop["id"]).first()
                if db_prop and db_prop.latitude and db_prop.longitude:
                    raw_data = await loop.run_in_executor(None, get_amenities, float(db_prop.latitude), float(db_prop.longitude), 1500)
                    mapped = map_osm_amenities(raw_data)
                    
                    # Convert the mapped categories into a flat list of simple string badges with counts (e.g. "Hospital (2)", "Metro")
                    amenities_counts = {}
                    for category, items in mapped.items():
                        for item in items:
                            if item.get("type"):
                                # Clean up the type string (e.g. "public_transport" -> "Public Transport")
                                clean_type = str(item["type"]).replace("_", " ").title()
                                if clean_type:
                                    amenities_counts[clean_type] = amenities_counts.get(clean_type, 0) + 1
                    
                    # Format as "Name" or "Name (N)"
                    amenities = [
                        f"{name} ({count})" if count > 1 else name 
                        for name, count in list(amenities_counts.items())[:6]
                    ]
                db_session.close()
            except Exception as e:
                logger.error(f"Error enriching amenities for {prop['id']}: {e}")
                
            insights = ""
            try:
                locality = resolve_locality(prop, db_prop)
                if locality:
                    insights = await loop.run_in_executor(
                        None, format_insights_for_display, locality, "general"
                    )
            except Exception as e:
                logger.error(f"Error enriching insights for {prop['id']}: {e}")
                
            await safe_send_json(websocket, {
                "type": "property_update",
                "property_id": prop["id"],
                "amenities": amenities,
                "neighborhoodInsights": insights
            })
            # Sleep 1.5 seconds to avoid Overpass API 429 Too Many Requests
            await asyncio.sleep(1.5)

    async def send_greeting():
        """Synthesize and stream the greeting text + audio."""
        if state.history and len(state.history) > 0 and state.shortlist and len(state.shortlist) > 0:
            greeting = "Welcome back! Do you want to continue looking at these properties, or search for something else?"
            logger.info(f"Synthesizing resume greeting for session '{session_id}'")
            asyncio.create_task(enrich_properties_background(state.shortlist))
        else:
            greeting = GREETING_TEXT
            logger.info(f"Synthesizing greeting for session '{session_id}'")

        # 1. Send text immediately so UI shows the message
        await safe_send_json(websocket, {"type": "text", "content": greeting})
        state.add_message("assistant", greeting)

        # 2. Synthesize audio in a thread pool so we don't block the event loop
        loop = asyncio.get_event_loop()
        try:
            audio_bytes = await loop.run_in_executor(None, tts.synthesize_sync, greeting)
            if audio_bytes:
                logger.info(f"Greeting audio ready: {len(audio_bytes)} bytes — sending")
                await safe_send_bytes(websocket, audio_bytes)
            else:
                logger.warning("TTS returned empty audio for greeting")
        except Exception as e:
            logger.error(f"Greeting TTS error: {e}")

    async def handle_user_text(user_text: str):
        """Process a user message through the LLM and stream back TTS audio."""
        logger.info(f"Processing turn for session '{session_id}': {user_text}")
        try:
            full_response = await orchestrator.process_message(state, user_text)

            if full_response:
                await safe_send_json(websocket, {"type": "text", "content": full_response})

            if state.shortlist:
                await safe_send_json(websocket, {
                    "type": "shortlist", 
                    "properties": state.shortlist,
                    "preferences": state.preferences
                })
                
                asyncio.create_task(enrich_properties_background(state.shortlist))

            if full_response:
                import re
                # Clean markdown so TTS doesn't read "asterisk" or "hash"
                clean_tts_text = re.sub(r'[*#_~`]', '', full_response)
                loop = asyncio.get_event_loop()
                audio_bytes = await loop.run_in_executor(None, tts.synthesize_sync, clean_tts_text)
                if audio_bytes:
                    await safe_send_bytes(websocket, audio_bytes)

        except Exception as e:
            logger.error(f"Error handling user text in voice_stream: {e}")
            await safe_send_json(websocket, {
                "type": "text",
                "content": "I encountered an error processing your request. Please try again."
            })

    try:
        while True:
            message = await websocket.receive()

            if message.get("type") == "websocket.disconnect":
                logger.info(f"Client disconnected for session: {session_id}")
                break

            if "bytes" in message and message["bytes"]:
                audio_data = message["bytes"]
                logger.info(f"Received audio blob ({len(audio_data)} bytes)")

                loop = asyncio.get_event_loop()
                transcript = await loop.run_in_executor(None, stt.transcribe_audio, audio_data)

                if transcript:
                    await safe_send_json(websocket, {"type": "user_text", "content": transcript})
                    await handle_user_text(transcript)
                else:
                    logger.warning("No speech transcribed from audio blob.")

            elif "text" in message and message["text"]:
                try:
                    data = json.loads(message["text"])
                    msg_type = data.get("type")
                    if msg_type == "greeting":
                        await send_greeting()
                    elif msg_type == "text" and data.get("content"):
                        await handle_user_text(data["content"])
                except Exception as parse_err:
                    logger.error(f"Error parsing text frame: {parse_err}")

    except WebSocketDisconnect:
        logger.info(f"Client disconnected for session: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error in voice_stream: {e}")
    finally:
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.close()
        except Exception:
            pass
        logger.info(f"WebSocket session ended: {session_id}")
