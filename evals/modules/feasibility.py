import asyncio
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def evaluate_feasibility(
    expected_state: Dict[str, Any],
    bot_returned_properties: List[Dict[str, Any]],
    bot_commute_claims: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Evaluates feasibility of returned properties against user-state requirements.

    Rule-based checks:
      • property["rent"] <= expected_state["max_budget"]    (if budget set)
      • property["rooms"] >= expected_state["min_bhk"]      (if BHK set)
        NOTE: `rooms` is the key used by format_properties() in queries.py.

    LLM-assisted check (commute realism):
      bot_commute_claims format:
        [{"property_locality": "Indiranagar", "destination": "MG Road", "claimed_mins": 15}]
    """
    results: Dict[str, Any] = {
        "passed": True,
        "rule_based_passed": True,
        "llm_commute_passed": True,
        "llm_commute_skipped": False,
        "details": [],
    }

    max_budget: Optional[int] = expected_state.get("max_budget")
    req_min_bhk: Optional[int] = expected_state.get("min_bhk")

    # ── 1. Rule-based: budget and BHK ─────────────────────────────────────────
    for prop in bot_returned_properties:
        prop_id = prop.get("id", "<unknown>")

        if max_budget is not None:
            rent = prop.get("rent", 0)
            if rent > max_budget:
                results["rule_based_passed"] = False
                results["details"].append(
                    f"[FEASIBILITY] Property {prop_id} rent ₹{rent:,} exceeds budget ₹{max_budget:,}."
                )

        if req_min_bhk is not None:
            rooms = prop.get("rooms")  # key from format_properties() in queries.py
            if rooms is None or int(rooms) < int(req_min_bhk):
                results["rule_based_passed"] = False
                results["details"].append(
                    f"[FEASIBILITY] Property {prop_id} has {rooms} BHK, "
                    f"below required minimum of {req_min_bhk}."
                )

    # ── 2. LLM-assisted: commute realism ──────────────────────────────────────
    if bot_commute_claims:
        from evals.judges.llm_judge import judge

        for claim in bot_commute_claims:
            try:
                eval_result = await judge.evaluate_commute_realism(
                    property_locality=claim.get("property_locality", ""),
                    target_destination=claim.get("destination", ""),
                    claimed_time_mins=claim.get("claimed_mins", 0),
                )
                if eval_result.get("skipped"):
                    results["llm_commute_skipped"] = True
                    results["details"].append(
                        "[FEASIBILITY] Commute realism check skipped — GROQ_API_KEY not set."
                    )
                elif not eval_result.get("is_realistic", False):
                    results["llm_commute_passed"] = False
                    results["details"].append(
                        f"[FEASIBILITY] Unrealistic commute claim: {eval_result.get('reasoning')}"
                    )
            except Exception as exc:
                logger.error("Commute realism judge raised unexpectedly: %s", exc)
                results["details"].append(f"[FEASIBILITY] Commute judge error: {exc}")

    # If commute was skipped, don't penalise the overall pass
    if results["llm_commute_skipped"]:
        results["passed"] = results["rule_based_passed"]
    else:
        results["passed"] = results["rule_based_passed"] and results["llm_commute_passed"]

    return results
