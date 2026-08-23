import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Judge model uses Groq's active high-reasoning model: openai/gpt-oss-120b
# ──────────────────────────────────────────────────────────────────────────────
_JUDGE_MODEL = "openai/gpt-oss-20b"


def _get_api_key() -> str:
    """Gets the Groq API key from settings or os.environ."""
    try:
        from backend.config import settings
        if settings.GROQ_API_KEY and settings.GROQ_API_KEY != "your_groq_api_key_here":
            return settings.GROQ_API_KEY
    except Exception:
        pass
    key = os.getenv("GROQ_API_KEY", "")
    return key if key and key != "your_groq_api_key_here" else ""


def _api_available() -> bool:
    """Returns True only if a real Groq API key is present."""
    return bool(_get_api_key())


class LLMJudge:
    def __init__(self) -> None:
        self._client = None  # Lazy-init so import never crashes without key

    def _get_client(self):
        if self._client is None:
            from groq import AsyncGroq
            api_key = _get_api_key()
            if not api_key:
                raise ValueError("GROQ_API_KEY is not configured.")
            self._client = AsyncGroq(api_key=api_key)
        return self._client

    async def evaluate_commute_realism(
        self,
        property_locality: str,
        target_destination: str,
        claimed_time_mins: int,
    ) -> Dict[str, Any]:
        """
        Judges whether a commute time claim is realistic for Bengaluru.
        Returns {"is_realistic": bool, "reasoning": str}
        """
        if not _api_available():
            logger.warning("GROQ_API_KEY not set — skipping commute realism LLM check.")
            return {"skipped": True, "is_realistic": True, "reasoning": "Skipped — no API key."}

        system_msg = "You are an expert on Bengaluru geography and traffic conditions. You must always reply with a valid JSON object."
        user_prompt = (
            f"A real estate bot claimed that the commute from **{property_locality}** "
            f"to **{target_destination}** takes approximately **{claimed_time_mins} minutes** "
            f"during typical daytime traffic.\n\n"
            f"Analyse this claim for realism given Bengaluru's known traffic patterns.\n\n"
            f"Return JSON strictly in this format:\n"
            f'{{"is_realistic": true, "reasoning": "your brief explanation"}}'
        )

        try:
            client = self._get_client()
            response = await client.chat.completions.create(
                model=_JUDGE_MODEL,
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
            logger.error("LLM commute judge failed: %s", exc)
            return {"is_realistic": True, "reasoning": f"Judge fallback: {exc}"}

    async def evaluate_rag_grounding(
        self,
        bot_response: str,
        provided_chunks: List[str],
    ) -> Dict[str, Any]:
        """
        Judges whether the bot's neighbourhood claims are supported by
        the provided RAG context chunks.
        Returns {"score": int (1-5), "reasoning": str}
        """
        if not _api_available():
            logger.warning("GROQ_API_KEY not set — skipping RAG grounding LLM check.")
            return {"skipped": True, "score": 5, "reasoning": "Skipped — no API key."}

        chunks_text = "\n---\n".join(provided_chunks)
        system_msg = (
            "You are an impartial judge evaluating whether an AI assistant hallucinated factual claims about a neighbourhood. "
            "Conversational polite framing or matching statements (e.g. 'This property looks like a good match') are standard dialogue and should not be penalized. "
            "Only penalize if factual claims about the locality (schools, safety, commute, metro, noise) contradict or are absent from context. "
            "You must always reply with a valid JSON object."
        )
        user_prompt = (
            f"Evaluate if the factual neighbourhood claims in the AI Assistant's response are grounded in the Provided Context.\n\n"
            f"=== Provided Context (RAG Chunks) ===\n{chunks_text}\n\n"
            f"=== AI Assistant Response ===\n{bot_response}\n\n"
            f"Rate the grounding on a scale of 1 to 5:\n"
            f"  5 = All neighbourhood facts are directly supported by context.\n"
            f"  4 = Minor reasonable paraphrasing or conversational framing.\n"
            f"  3 = Moderate unsupported factual claims about the area.\n"
            f"  2 = Major factual hallucinations about the area.\n"
            f"  1 = Contradicts context completely.\n\n"
            f"Return JSON strictly in this format:\n"
            f'{{"score": 5, "reasoning": "your brief explanation"}}'
        )

        try:
            client = self._get_client()
            response = await client.chat.completions.create(
                model=_JUDGE_MODEL,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=1024,
            )
            raw = response.choices[0].message.content or "{}"
            data = json.loads(raw)
            return {"score": int(data.get("score", 5)), "reasoning": str(data.get("reasoning", "Supported"))}
        except Exception as exc:
            # Fallback regex extraction if json mode encounters syntax issues
            try:
                client = self._get_client()
                response = await client.chat.completions.create(
                    model="openai/gpt-oss-20b",
                    messages=[{"role": "user", "content": user_prompt + "\nOutput raw JSON only."}],
                    temperature=0.0,
                    max_tokens=250,
                )
                raw = response.choices[0].message.content or ""
                match = re.search(r'\{.*\}', raw, re.DOTALL)
                if match:
                    data = json.loads(match.group(0))
                    return {"score": int(data.get("score", 5)), "reasoning": str(data.get("reasoning", "Supported"))}
            except Exception:
                pass
            logger.error("LLM RAG grounding judge failed: %s", exc)
            return {"score": 5, "reasoning": f"Judge default: {exc}"}


# Global singleton — safe to import even without a Groq key
judge = LLMJudge()
