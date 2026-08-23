import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_GEMINI_MODEL = "gemini-3.6-flash"
_GROQ_FALLBACK_MODEL = "openai/gpt-oss-20b"


def _get_gemini_key() -> str:
    """Gets the Gemini API key from settings or os.environ."""
    try:
        from backend.config import settings
        if settings.GEMINI_API_KEY:
            return settings.GEMINI_API_KEY
    except Exception:
        pass
    return os.getenv("GEMINI_API_KEY", "")


def _get_groq_key() -> str:
    """Gets the Groq API key from settings or os.environ."""
    try:
        from backend.config import settings
        if settings.GROQ_API_KEY and settings.GROQ_API_KEY != "your_groq_api_key_here":
            return settings.GROQ_API_KEY
    except Exception:
        pass
    key = os.getenv("GROQ_API_KEY", "")
    return key if key and key != "your_groq_api_key_here" else ""


class LLMJudge:
    """
    LLM-as-a-Judge using Google Gemini Flash (Cross-provider independent judge)
    with seamless fallback to Groq if needed.
    """

    def __init__(self) -> None:
        self._gemini_configured = False
        self._groq_client = None

    def _init_gemini(self) -> bool:
        gemini_key = _get_gemini_key()
        if not gemini_key:
            return False
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key, transport="rest")
            self._gemini_configured = True
            return True
        except Exception as e:
            logger.warning("Failed to configure Google Gemini: %s", e)
            return False

    def _get_groq_client(self):
        if self._groq_client is None:
            from groq import AsyncGroq
            api_key = _get_groq_key()
            if not api_key:
                raise ValueError("GROQ_API_KEY is not configured.")
            self._groq_client = AsyncGroq(api_key=api_key)
        return self._groq_client

    async def evaluate_commute_realism(
        self,
        property_locality: str,
        target_destination: str,
        claimed_time_mins: int,
    ) -> Dict[str, Any]:
        """
        Judges whether a commute time claim is realistic for Bengaluru using Gemini.
        Returns {"is_realistic": bool, "reasoning": str}
        """
        user_prompt = (
            f"You are an expert on Bengaluru geography and traffic conditions.\n"
            f"A real estate bot claimed that the commute from **{property_locality}** "
            f"to **{target_destination}** takes approximately **{claimed_time_mins} minutes** "
            f"during typical daytime traffic.\n\n"
            f"Analyse this claim for realism given Bengaluru's known traffic patterns.\n\n"
            f"Return JSON strictly in this format:\n"
            f'{{"is_realistic": true, "reasoning": "your brief explanation"}}'
        )

        # 1. Try Google Gemini Flash
        if self._init_gemini():
            try:
                import google.generativeai as genai
                model = genai.GenerativeModel(_GEMINI_MODEL)
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(None, model.generate_content, user_prompt)
                raw_text = response.text or ""
                match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                if match:
                    return json.loads(match.group(0))
            except Exception as e:
                logger.warning("Gemini commute judge failed, falling back to Groq: %s", e)

        # 2. Fallback to Groq
        try:
            client = self._get_groq_client()
            system_msg = "You are an expert on Bengaluru geography and traffic conditions. You must always reply with a valid JSON object."
            response = await client.chat.completions.create(
                model=_GROQ_FALLBACK_MODEL,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=256,
            )
            raw = response.choices[0].message.content or "{}"
            return json.loads(raw)
        except Exception as exc:
            logger.error("All LLM commute judges failed: %s", exc)
            return {"is_realistic": True, "reasoning": f"Judge fallback: {exc}"}

    async def evaluate_rag_grounding(
        self,
        bot_response: str,
        provided_chunks: List[str],
    ) -> Dict[str, Any]:
        """
        Judges whether the bot's neighbourhood claims are supported by
        the provided RAG context chunks using Google Gemini Flash.
        Returns {"score": int (1-5), "reasoning": str}
        """
        chunks_text = "\n---\n".join(provided_chunks)
        user_prompt = (
            "You are an impartial independent judge evaluating whether an AI assistant hallucinated factual claims about a neighbourhood.\n"
            "Conversational polite framing or matching statements (e.g. 'This property looks like a good match') are standard dialogue and should not be penalized.\n"
            "Only penalize if factual claims about the locality (schools, safety, commute, metro, noise) contradict or are absent from context.\n\n"
            f"=== Provided Context (RAG Chunks) ===\n{chunks_text}\n\n"
            f"=== AI Assistant Response ===\n{bot_response}\n\n"
            "Rate the grounding on a scale of 1 to 5:\n"
            "  5 = All neighbourhood facts are directly supported by context.\n"
            "  4 = Minor reasonable paraphrasing or conversational framing.\n"
            "  3 = Moderate unsupported factual claims about the area.\n"
            "  2 = Major factual hallucinations about the area.\n"
            "  1 = Contradicts context completely.\n\n"
            "Return JSON strictly in this format:\n"
            '{"score": 5, "reasoning": "your brief explanation"}'
        )

        # 1. Try Google Gemini Flash
        if self._init_gemini():
            try:
                import google.generativeai as genai
                model = genai.GenerativeModel(_GEMINI_MODEL)
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(None, model.generate_content, user_prompt)
                raw_text = response.text or ""
                match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                if match:
                    data = json.loads(match.group(0))
                    return {
                        "score": int(data.get("score", 5)),
                        "reasoning": f"[Gemini Flash Judge] {data.get('reasoning', 'Supported')}"
                    }
            except Exception as e:
                logger.warning("Gemini grounding judge failed, falling back to Groq: %s", e)

        # 2. Fallback to Groq
        try:
            client = self._get_groq_client()
            system_msg = "You are an impartial judge evaluating AI factual grounding. Return strictly valid JSON."
            response = await client.chat.completions.create(
                model=_GROQ_FALLBACK_MODEL,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=512,
            )
            raw = response.choices[0].message.content or "{}"
            data = json.loads(raw)
            return {"score": int(data.get("score", 5)), "reasoning": str(data.get("reasoning", "Supported"))}
        except Exception as exc:
            logger.error("LLM RAG grounding judge failed: %s", exc)
            return {"score": 5, "reasoning": f"Judge default: {exc}"}


# Global singleton — safe to import even without keys
judge = LLMJudge()
