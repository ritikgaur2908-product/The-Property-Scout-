import asyncio
import json
import logging
import re
from typing import Any, AsyncGenerator, Dict, List, Optional

from groq import AsyncGroq

from backend.config import settings
from backend.db.connection import SessionLocal
from backend.db.queries import search_properties_in_db
from backend.llm.prompts import get_system_prompt
from backend.llm.state_manager import ConversationState
from backend.llm.tools import get_tools
from backend.notification.payloads import build_shortlist_payload
from backend.notification.webhook import is_webhook_configured, _send_webhook_async

logger = logging.getLogger(__name__)

# Prefer the smaller OSS model when available to reduce TPM pressure; fall back to 120b for tool calling.
_PREFERRED_MODEL = "openai/gpt-oss-20b"
_TOOL_MODEL = "openai/gpt-oss-20b"

_USERFacing_REPLACEMENTS = (
    (re.compile(r"\bdatabase\b", re.IGNORECASE), "my records"),
    (re.compile(r"\btool response\b", re.IGNORECASE), "what I found"),
    (re.compile(r"\btool call\b", re.IGNORECASE), "lookup"),
    (re.compile(r"\bAPI\b", re.IGNORECASE), "service"),
    (re.compile(r"\bbackend\b", re.IGNORECASE), "system"),
    (re.compile(r"\bRAG\b", re.IGNORECASE), "neighborhood sources"),
    (re.compile(r"my search didn'?t return", re.IGNORECASE), "I couldn't find"),
    (re.compile(r"my search returned no", re.IGNORECASE), "I found no"),
    (re.compile(r"the search returned", re.IGNORECASE), "I found"),
    (re.compile(r"no results were returned", re.IGNORECASE), "nothing matched"),
    (re.compile(r"returned by the", re.IGNORECASE), "available"),
)


class Orchestrator:
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY, max_retries=0)
        self.model = settings.LLM_MODEL or _TOOL_MODEL
        self.tools = get_tools()

    def _sanitize_user_response(self, text: str) -> str:
        if not text:
            return text
        sanitized = text
        for pattern, replacement in _USERFacing_REPLACEMENTS:
            sanitized = pattern.sub(replacement, sanitized)
        return sanitized

    async def _dispatch_shortlist_email(self, state: ConversationState, email: str) -> dict:
        if not email or "@" not in email:
            return {
                "status": "error",
                "message": "A valid email address is required before sending the shortlist.",
            }
        if not state.shortlist:
            return {
                "status": "error",
                "message": "There is no shortlist to email yet. Run a property search first.",
            }
        if not is_webhook_configured():
            return {
                "status": "error",
                "message": (
                    "Email delivery isn't available right now. "
                    "Please let the user know they can use the \"Email Shortlist\" button "
                    "on the right panel to send the shortlist directly."
                ),
            }

        state.user_email = email.strip()
        payload = build_shortlist_payload(state.user_email, state.shortlist)
        from backend.config import settings
        path = settings.N8N_SHORTLIST_WEBHOOK_PATH
        sent = await _send_webhook_async("shortlist_mailed", payload, path)
        if sent:
            return {
                "status": "success",
                "message": f"Shortlist email sent to {state.user_email}.",
            }
        return {
            "status": "error",
            "message": (
                "I couldn't deliver the email right now. Please try again in a moment "
                "or use the Email Shortlist button on the right."
            ),
        }

    def _parse_rate_limit_wait(self, err_str: str) -> Optional[float]:
        match = re.search(r"try again in ([0-9.]+)s", err_str, re.IGNORECASE)
        if match:
            return float(match.group(1)) + 1.0
        return None

    async def _chat_with_retry(self, **kwargs: Any):
        max_attempts = 5
        last_error: Optional[Exception] = None

        for attempt in range(max_attempts):
            try:
                return await self.client.chat.completions.create(**kwargs)
            except Exception as exc:
                last_error = exc
                err_str = str(exc)
                if "429" in err_str or "rate_limit" in err_str.lower():
                    wait = self._parse_rate_limit_wait(err_str) or min(2 ** attempt * 2, 30)
                    logger.warning(
                        "Groq rate limit (attempt %s/%s), waiting %.1fs",
                        attempt + 1,
                        max_attempts,
                        wait,
                    )
                    await asyncio.sleep(wait)
                    continue
                raise

        raise last_error or RuntimeError("Groq request failed after retries")

    def _build_fallback_response(self, state: ConversationState) -> Optional[str]:
        if not state.shortlist:
            return None

        count = len(state.shortlist)
        loc = ""
        if state.preferences.get("localities"):
            loc = f" in {', '.join(state.preferences['localities'])}"
        return (
            f"I found {count} {'property' if count == 1 else 'properties'} matching your preferences{loc}. "
            "I've pulled up the listings on your right — take a look and let me know if you'd like to refine or book a visit!"
        )

    async def _yield_final_response(
        self,
        state: ConversationState,
        messages: List[Dict[str, Any]],
        *,
        use_tools: bool = False,
    ) -> AsyncGenerator[str, None]:
        kwargs: Dict[str, Any] = {
            "model": _PREFERRED_MODEL,
            "messages": messages,
            "max_tokens": 1024,
            "stream": False,
        }
        if use_tools:
            kwargs["tools"] = self.tools
    async def _yield_final_response(
        self,
        state: ConversationState,
        messages: List[Dict[str, Any]],
        *,
        use_tools: bool = False,
    ) -> AsyncGenerator[str, None]:
        kwargs: Dict[str, Any] = {
            "model": _PREFERRED_MODEL,
            "messages": messages,
            "max_tokens": 256,
            "stream": False,
        }
        if use_tools:
            kwargs["tools"] = self.tools
            kwargs["tool_choice"] = "auto"

        try:
            response = await asyncio.wait_for(
                self._chat_with_retry(**kwargs),
                timeout=12.0,
            )
            final_content = response.choices[0].message.content or ""
            if final_content:
                final_content = self._sanitize_user_response(final_content)
                yield final_content
                state.add_message("assistant", final_content)
                return
        except Exception as exc:
            logger.error("Final LLM response exception (or rate limit): %s", exc)
            # If we have locality & budget but shortlist wasn't fetched yet, query DB directly
            if not state.shortlist and state.preferences.get("localities") and state.preferences.get("max_budget"):
                db_fallback = SessionLocal()
                try:
                    props, _ = search_properties_in_db(db_fallback, state.preferences, limit=6)
                    if props:
                        state.shortlist = props
                except Exception as dbe:
                    logger.error("DB fallback search failed: %s", dbe)
                finally:
                    db_fallback.close()

            fallback = self._build_fallback_response(state)
            if fallback:
                yield fallback
                state.add_message("assistant", fallback)
                return
            if "429" in str(exc) or "rate_limit" in str(exc).lower():
                yield (
                    "I found your matching listings and have displayed them on the screen. "
                    "Let me know if you would like to adjust the budget or locality!"
                )
                return
            yield "I'm sorry, I encountered an internal error while processing your request."
            return

        fallback = self._build_fallback_response(state)
        if fallback:
            yield fallback
            state.add_message("assistant", fallback)

    async def process_message(self, state: ConversationState, user_message: str) -> str:
        generator = self.process_message_stream(state, user_message)
        final_text = ""
        async for chunk in generator:
            final_text += chunk
        return final_text

    async def process_message_stream(
        self, state: ConversationState, user_message: str
    ) -> AsyncGenerator[str, None]:
        state.add_message("user", user_message)

        # Truncate history to last 6 messages to stay well under Groq 6000 TPM limit
        trimmed_history = state.history[-6:]
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": get_system_prompt(state.preferences)}
        ]
        messages.extend(trimmed_history)

        db_session = SessionLocal()
        pending_final = False

        try:
            while True:
                try:
                    response = await self._chat_with_retry(
                        model=self.model,
                        messages=messages,
                        tools=self.tools,
                        tool_choice="auto",
                        max_tokens=256,
                        stream=False,
                    )
                except Exception as tool_err:
                    err_str = str(tool_err)
                    if "tool_use_failed" in err_str or "Failed to call a function" in err_str:
                        logger.warning("Tool calling failed, attempting recovery: %s", err_str)
                        match = re.search(r"<function=(\w+)\s+(.*?)</function>", err_str)
                        if match:
                            func_name = match.group(1)
                            func_args_str = match.group(2).strip()
                            logger.info(
                                "Recovered tool call: %s with %s", func_name, func_args_str
                            )

                            try:
                                function_args = json.loads(func_args_str)
                            except json.JSONDecodeError:
                                function_args = {}

                            tool_result = ""
                            if func_name == "search_properties":
                                state.update_preferences(function_args)

                                if not state.shortlist and (
                                    not state.preferences.get("max_budget")
                                    or not state.preferences.get("localities")
                                ):
                                    tool_result = json.dumps(
                                        {
                                            "status": "error",
                                            "warning": (
                                                "FIRST-SEARCH GATE FAILED: You must collect BOTH "
                                                "max_budget and locality before calling search_properties."
                                            ),
                                        }
                                    )
                                else:
                                    old_properties = {p["id"]: p for p in state.shortlist}
                                    properties, warning = search_properties_in_db(
                                        db_session, state.preferences
                                    )
                                    for p in properties:
                                        if p["id"] in old_properties:
                                            old_p = old_properties[p["id"]]
                                            if "amenities" in old_p:
                                                p["amenities"] = old_p["amenities"]
                                            if "neighborhoodInsights" in old_p:
                                                p["neighborhoodInsights"] = old_p["neighborhoodInsights"]
                                    state.shortlist = properties
                                    res_dict = {"status": "success", "results": properties}
                                    if warning:
                                        res_dict["warning"] = warning
                                    tool_result = json.dumps(res_dict)

                            messages.append(
                                {
                                    "role": "assistant",
                                    "content": None,
                                    "tool_calls": [
                                        {
                                            "id": "call_recovered_123",
                                            "type": "function",
                                            "function": {
                                                "name": func_name,
                                                "arguments": func_args_str,
                                            },
                                        }
                                    ],
                                }
                            )
                            messages.append(
                                {
                                    "tool_call_id": "call_recovered_123",
                                    "role": "tool",
                                    "name": func_name,
                                    "content": tool_result,
                                }
                            )
                            pending_final = True
                            break
                        logger.warning("Could not parse failed generation. Breaking to final response.")
                        pending_final = True
                        break
                    raise

                response_message = response.choices[0].message

                if not response_message.tool_calls:
                    final_content = self._sanitize_user_response(response_message.content or "")
                    yield final_content
                    state.add_message("assistant", final_content)
                    return

                messages.append(response_message)

                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name
                    try:
                        function_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError as je:
                        logger.error("Failed to parse tool args for %s: %s", function_name, je)
                        function_args = {}

                    logger.info(
                        "LLM called tool: %s with args: %s", function_name, function_args
                    )

                    tool_result = ""

                    if function_name == "search_properties":
                        state.update_preferences(function_args)

                        if not state.shortlist and (
                            not state.preferences.get("max_budget")
                            or not state.preferences.get("localities")
                        ):
                            tool_result = json.dumps(
                                {
                                    "status": "error",
                                    "warning": (
                                        "FIRST-SEARCH GATE FAILED: You must collect BOTH max_budget "
                                        "and locality before calling search_properties."
                                    ),
                                }
                            )
                        else:
                            old_properties = {p["id"]: p for p in state.shortlist}
                            properties, warning = search_properties_in_db(
                                db_session, state.preferences
                            )
                            for p in properties:
                                if p["id"] in old_properties:
                                    old_p = old_properties[p["id"]]
                                    if "amenities" in old_p:
                                        p["amenities"] = old_p["amenities"]
                                    if "neighborhoodInsights" in old_p:
                                        p["neighborhoodInsights"] = old_p["neighborhoodInsights"]
                            state.shortlist = properties
                            res_dict = {"status": "success", "results": properties}
                            if warning:
                                res_dict["warning"] = warning
                            tool_result = json.dumps(res_dict)

                    elif function_name == "get_neighborhood_info":
                        from backend.rag.synthesizer import synthesize_neighborhood_info

                        rag_context = synthesize_neighborhood_info(
                            locality=function_args.get("locality", ""),
                            topic=function_args.get("topic", "general"),
                        )
                        target_loc = function_args.get("locality", "").lower()
                        for p in state.shortlist:
                            p_loc = p.get("locality", "").lower()
                            if target_loc in p_loc or target_loc in p.get("address", "").lower():
                                p["neighborhoodInsights"] = rag_context
                        tool_result = json.dumps({"status": "success", "info": rag_context})

                    elif function_name == "get_amenities":
                        property_id = function_args.get("property_id")
                        if not property_id:
                            tool_result = json.dumps(
                                {"status": "error", "message": "Missing property_id"}
                            )
                        else:
                            from backend.db.models import Property
                            from backend.mcp.amenity_mapper import map_osm_amenities
                            from backend.mcp.osm_client import get_amenities

                            prop = (
                                db_session.query(Property)
                                .filter(Property.id == property_id)
                                .first()
                            )

                            if not prop or not prop.latitude or not prop.longitude:
                                tool_result = json.dumps(
                                    {
                                        "status": "error",
                                        "message": "Property not found or missing coordinates.",
                                    }
                                )
                            else:
                                raw_data = get_amenities(
                                    float(prop.latitude), float(prop.longitude), 1500
                                )
                                mapped_amenities = map_osm_amenities(raw_data)
                                for p in state.shortlist:
                                    if str(p["id"]) == str(property_id):
                                        p["amenities"] = mapped_amenities
                                        break
                                tool_result = json.dumps(
                                    {"status": "success", "amenities": mapped_amenities}
                                )

                    elif function_name == "book_visit":
                        property_id = function_args.get("property_id")
                        date = function_args.get("date")
                        time = function_args.get("time")
                        email = function_args.get("email")

                        try:
                            from backend.booking.service import (
                                BookingConflictError,
                                create_booking,
                            )

                            booking = create_booking(
                                db_session, property_id, email, date, time
                            )
                            tool_result = json.dumps(
                                {
                                    "status": "success",
                                    "booking_id": booking.booking_id,
                                    "message": "Booking confirmed successfully.",
                                }
                            )
                        except BookingConflictError as exc:
                            tool_result = json.dumps(
                                {
                                    "status": "conflict",
                                    "message": "The requested time slot is already booked.",
                                    "alternative_slots": exc.alternative_slots,
                                }
                            )
                        except Exception as exc:
                            logger.error("Booking error: %s", exc)
                            tool_result = json.dumps({"status": "error", "message": str(exc)})

                    elif function_name == "send_shortlist_email":
                        email = function_args.get("email") or state.user_email
                        tool_result = json.dumps(await self._dispatch_shortlist_email(state, email))

                    else:
                        tool_result = json.dumps({"status": "error", "message": "Unknown tool."})

                    messages.append(
                        {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": tool_result,
                        }
                    )

            if pending_final or messages[-1]["role"] == "tool":
                async for chunk in self._yield_final_response(state, messages):
                    yield chunk

        except Exception as exc:
            logger.error("Error in orchestrator loop: %s", exc)
            fallback = self._build_fallback_response(state)
            if fallback:
                yield fallback
                state.add_message("assistant", fallback)
            elif "429" in str(exc) or "rate_limit" in str(exc).lower():
                yield (
                    "I'm a bit overwhelmed with requests right now. "
                    "Could you please try again in a moment?"
                )
            else:
                yield "I'm sorry, I encountered an internal error while processing your request."
        finally:
            db_session.close()
