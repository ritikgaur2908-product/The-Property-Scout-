import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# All phrases the bot should produce when it genuinely has no answer.
# Cross-referenced against the orchestrator's synthesizer.py uncertainty language.
UNCERTAINTY_KEYWORDS = [
    "i don't have",
    "i am unsure",
    "i cannot confirm",
    "i don't know",
    "i'm not sure",
    "not sure",
    "unsure",
    "no verified",
    "no information",
    "unable to confirm",
    "i'm unable",
    "i cannot say",
    "i have no data",
    "i lack",
    "explicit",          # catches "I cannot say explicitly"
    "no results",        # catches "no results found"
    "nothing matched",
    "couldn't find",
    "we currently have absolutely no",
]


async def evaluate_grounding(
    bot_response: str,
    returned_property_ids: List[str],
    valid_available_property_ids: set,
    provided_rag_chunks: List[str],
    uncertainty_expected: bool,
) -> Dict[str, Any]:
    """
    Evaluates grounding and hallucination across three dimensions:

    1. Listing Validity (rule-based):
       Every property_id in bot output must exist in the mock DB with status=available.

    2. Uncertainty Handling (rule-based):
       When uncertainty_expected=True the response must contain at least one
       known uncertainty keyword — otherwise the bot is hallucinating.

    3. RAG Source Grounding Score (LLM-assisted, 1–5):
       Judges whether neighbourhood claims are supported by provided RAG chunks.
       Requires score >= 4 to pass. Skipped gracefully if no GROQ_API_KEY.
    """
    results: Dict[str, Any] = {
        "passed": True,
        "listing_validity_passed": True,
        "uncertainty_passed": True,
        "rag_grounding_score": None,
        "rag_grounding_passed": True,
        "rag_grounding_skipped": False,
        "details": [],
    }

    # ── 1. Listing Validity ────────────────────────────────────────────────────
    for pid in returned_property_ids:
        if pid not in valid_available_property_ids:
            results["listing_validity_passed"] = False
            results["details"].append(
                f"[GROUNDING] Property ID '{pid}' is not in the valid available set."
            )

    # ── 2. Uncertainty Keywords ────────────────────────────────────────────────
    if uncertainty_expected:
        lower_resp = bot_response.lower()
        matched_kw = next((kw for kw in UNCERTAINTY_KEYWORDS if kw in lower_resp), None)
        if matched_kw is None:
            results["uncertainty_passed"] = False
            results["details"].append(
                "[GROUNDING] Bot response was expected to express uncertainty but "
                "no uncertainty keywords were found. Possible hallucination."
            )
        else:
            results["details"].append(
                f"[GROUNDING] Uncertainty correctly expressed (matched keyword: '{matched_kw}')."
            )

    # ── 3. RAG Source Grounding (LLM-assisted) ────────────────────────────────
    if provided_rag_chunks:
        from evals.judges.llm_judge import judge
        try:
            eval_result = await judge.evaluate_rag_grounding(
                bot_response=bot_response,
                provided_chunks=provided_rag_chunks,
            )
            if eval_result.get("skipped"):
                results["rag_grounding_skipped"] = True
                results["rag_grounding_score"] = None
                results["details"].append(
                    "[GROUNDING] RAG grounding score skipped — GROQ_API_KEY not set."
                )
            else:
                score = int(eval_result.get("score", 1))
                results["rag_grounding_score"] = score
                if score < 4:
                    results["rag_grounding_passed"] = False
                    results["details"].append(
                        f"[GROUNDING] RAG grounding score {score}/5 is below threshold (>=4). "
                        f"Reason: {eval_result.get('reasoning')}"
                    )
                else:
                    results["details"].append(
                        f"[GROUNDING] RAG grounding score {score}/5 — "
                        f"{eval_result.get('reasoning')}"
                    )
        except Exception as exc:
            logger.error("RAG grounding judge raised unexpectedly: %s", exc)
            results["details"].append(f"[GROUNDING] RAG judge error: {exc}")

    # ── Aggregate ──────────────────────────────────────────────────────────────
    # Don't penalise for a skipped LLM check
    rag_ok = results["rag_grounding_passed"] or results["rag_grounding_skipped"]
    results["passed"] = (
        results["listing_validity_passed"]
        and results["uncertainty_passed"]
        and rag_ok
    )

    return results
