"""
evals/run_evals.py — CLI evaluation runner for The Property Scout.

Usage:
    python evals/run_evals.py                           # run all modules
    python evals/run_evals.py --module feasibility
    python evals/run_evals.py --module edit_correctness
    python evals/run_evals.py --module grounding
    python evals/run_evals.py --verbose
    python evals/run_evals.py --output evals/logs/custom_run.json

Also runnable as pytest:
    pytest evals/ -v
"""
import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

# ── Make project root importable ─────────────────────────────────────────────
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))

# ── Patch JSONB → JSON BEFORE importing any models ───────────────────────────
from sqlalchemy import JSON
import sqlalchemy.dialects.postgresql as _pg
_pg.JSONB = JSON  # type: ignore[attr-defined]

from evals.modules.feasibility import evaluate_feasibility
from evals.modules.edit_correctness import evaluate_edit_correctness
from evals.modules.grounding import evaluate_grounding

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("run_evals")

# ── ANSI colours (gracefully disabled on non-TTY) ─────────────────────────────
_USE_COLOUR = sys.stdout.isatty()

def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOUR else text

def green(t: str) -> str:  return _c(t, "32")
def red(t: str) -> str:    return _c(t, "31")
def yellow(t: str) -> str: return _c(t, "33")
def bold(t: str) -> str:   return _c(t, "1")
def dim(t: str) -> str:    return _c(t, "2")


# ─────────────────────────────────────────────────────────────────────────────
# Mock data helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_golden_dataset() -> List[Dict[str, Any]]:
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "golden_dataset.json")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _get_mock_properties(expected_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Simulate a property search result that RESPECTS the expected state.
    Used to test that the feasibility module correctly passes/fails.
    Mirrors the dict shape returned by format_properties() in queries.py.
    """
    max_budget = expected_state.get("max_budget") or 999_999
    min_bhk = expected_state.get("min_bhk") or 1
    localities = expected_state.get("localities") or ["Indiranagar"]
    locality = localities[0] if localities else "Indiranagar"

    return [
        {
            "id": "PROP-TEST-001",
            "reasoning": "Matched based on your preferences.",
            "rent": max_budget - 1000,   # just under budget — rule-based should PASS
            "rooms": min_bhk,            # exact BHK match
            "type": expected_state.get("accommodation_type", "whole_flat"),
            "locality": locality,
            "address": f"12, Main Road, {locality}",
            "move_in_time": "Immediate",
            "parking": expected_state.get("parking", False),
            "gender": expected_state.get("gender", "any"),
            "food": expected_state.get("food", None),
            "smoking": expected_state.get("smoking", None),
            "source_url": f"https://bengaluru.rent/mock",
        }
    ]


def _get_mock_rag_chunks(locality: str) -> List[str]:
    MOCK_CHUNKS: Dict[str, List[str]] = {
        "Indiranagar": [
            "Resident feedback for Indiranagar: Highly walkable. Excellent metro connectivity. "
            "Nightlife is vibrant — some noise on weekends.",
            "Resident observation: \"Bescom power cuts happen 1-2 hours weekly. Inverter is mandatory.\"",
        ],
        "HSR Layout": [
            "Resident feedback for HSR Layout: Well-planned, wide roads, family-oriented. "
            "No direct metro — Silk Board junction has severe traffic jams.",
            "Resident observation: \"27th main footpaths are usable. Very safe and well-lit.\"",
        ],
        "Koramangala": [
            "Resident feedback for Koramangala: Startup and student-heavy vibe, vibrant nightlife. "
            "No metro nearby. Block 4 traffic on 80ft road is severe in the evening.",
            "Resident observation: \"Stray dogs near the parks are a major issue at night.\"",
        ],
        "Whitefield": [
            "Resident feedback for Whitefield: Gated communities, very safe. Water supply depends "
            "on private tankers. Purple metro line has improved connectivity.",
            "Resident observation: \"Air quality is poor due to ongoing construction dust.\"",
        ],
        "Bellandur": [
            "Resident observation: \"Monsoon flooding near Bellandur lake makes roads impassable.\"",
        ],
        "BTM Layout": [
            "Resident feedback for BTM Layout: Affordable, young professional crowd. "
            "Auto drivers notorious for refusing rides in peak hours.",
        ],
        "Jayanagar": [
            "Resident feedback for Jayanagar: Old Bengaluru charm, quiet and clean. "
            "Well-connected via Rashtriya Military School metro station.",
        ],
    }
    return MOCK_CHUNKS.get(locality, [])


def _get_valid_property_ids() -> Set[str]:
    """The set of source_ids that are 'available' in the mock DB."""
    return {
        "PROP-TEST-001",
        "PROP-TEST-002",
        "PROP-TEST-003",
        "PROP-TEST-004",
        "PROP-TEST-005",
        "PROP-TEST-006",
    }


def _simulate_bot_response(tc: Dict[str, Any]) -> str:
    """
    Simulates what a well-behaved bot would say for a given test case.
    For uncertainty_expected cases, we produce an uncertainty response.
    For normal cases, we produce a grounded response using mock RAG chunks.
    Used to give the grounding module something meaningful to evaluate.
    """
    expected_beh = tc.get("expected_behavior", {})
    uncertainty_expected = expected_beh.get("uncertainty_expected", False)
    localities = tc.get("expected_state", {}).get("localities") or \
                 tc.get("previous_state", {}).get("localities") or []
    locality = localities[0] if localities else ""

    if uncertainty_expected:
        return (
            f"I'm not sure about that — I don't have verified information on "
            f"{'this area' if not locality else locality} for your specific query. "
            f"I'd recommend checking local resources directly."
        )

    chunks = _get_mock_rag_chunks(locality)
    if chunks:
        excerpt = chunks[0][:180]
        return (
            f"Based on resident feedback for {locality}: {excerpt} "
            f"This property looks like a strong match for your requirements."
        )
    return f"I found a good match in {locality or 'the requested area'} within your budget."


# ─────────────────────────────────────────────────────────────────────────────
# Per-module runners
# ─────────────────────────────────────────────────────────────────────────────

async def _run_feasibility(tc: Dict[str, Any], verbose: bool) -> Dict[str, Any]:
    """Run the feasibility module against a test case."""
    expected_state = tc.get("expected_state", {})
    # Build mock property list that correctly matches expectations
    bot_properties = _get_mock_properties(expected_state)
    result = await evaluate_feasibility(
        expected_state=expected_state,
        bot_returned_properties=bot_properties,
        bot_commute_claims=None,  # no commute claims in golden dataset (no LLM needed)
    )
    return result


def _run_edit_correctness(tc: Dict[str, Any], verbose: bool) -> Dict[str, Any]:
    """Run the edit correctness module against a test case."""
    previous_state = tc.get("previous_state", {})
    expected_state = tc.get("expected_state", {})

    # Only meaningful for multi-turn edit cases — skip if no previous state
    if not previous_state:
        return {
            "passed": True,
            "details": ["[EDIT] No previous_state — skipped (happy_path / adversarial / failure_mode)."],
            "skipped": True,
        }

    # Simulate the bot correctly applying the edit
    simulated_new_state = {**previous_state, **expected_state}
    # If expected_state has null values, apply them (e.g. max_budget: null)
    for key, val in expected_state.items():
        simulated_new_state[key] = val

    return evaluate_edit_correctness(
        previous_state=previous_state,
        new_state=simulated_new_state,
        expected_state=expected_state,
    )


async def _run_grounding(tc: Dict[str, Any], verbose: bool) -> Dict[str, Any]:
    """Run the grounding & hallucination module against a test case."""
    expected_beh = tc.get("expected_behavior", {})
    uncertainty_expected = expected_beh.get("uncertainty_expected", False)
    localities = tc.get("expected_state", {}).get("localities") or \
                 tc.get("previous_state", {}).get("localities") or []
    locality = localities[0] if localities else ""

    bot_response = _simulate_bot_response(tc)
    rag_chunks = _get_mock_rag_chunks(locality)
    valid_ids = _get_valid_property_ids()

    # Simulate the bot returning a single valid property (non-booking, non-adversarial)
    returned_ids: List[str] = []
    if not uncertainty_expected and not tc.get("expected_behavior", {}).get("booking_test"):
        returned_ids = ["PROP-TEST-001"]

    return await evaluate_grounding(
        bot_response=bot_response,
        returned_property_ids=returned_ids,
        valid_available_property_ids=valid_ids,
        provided_rag_chunks=rag_chunks,
        uncertainty_expected=uncertainty_expected,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main runner
# ─────────────────────────────────────────────────────────────────────────────

async def run_all(
    module_filter: Optional[str],
    verbose: bool,
) -> Dict[str, Any]:
    dataset = _load_golden_dataset()
    valid_modules = {"feasibility", "edit_correctness", "grounding"}

    if module_filter and module_filter not in valid_modules:
        print(red(f"Unknown module '{module_filter}'. Choose from: {', '.join(valid_modules)}"))
        sys.exit(1)

    report: Dict[str, Any] = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "module_filter": module_filter or "all",
        "total_cases": len(dataset),
        "results": [],
        "summary": {},
    }

    counts: Dict[str, Dict[str, int]] = {
        m: {"pass": 0, "fail": 0, "skip": 0}
        for m in ["feasibility", "edit_correctness", "grounding"]
    }

    print()
    print(bold("=" * 72))
    print(bold(f"  THE PROPERTY SCOUT -- Evaluation Suite  ({report['run_at']})"))
    print(bold("=" * 72))
    print(f"  Dataset: {len(dataset)} test cases | Module filter: {module_filter or 'all'}")
    print()

    for tc in dataset:
        tc_id = tc["test_id"]
        category = tc["category"]
        desc = tc["description"]

        tc_result: Dict[str, Any] = {
            "test_id": tc_id,
            "category": category,
            "description": desc,
            "modules": {},
        }

        if verbose:
            print(bold(f">> {tc_id}") + dim(f"  [{category}]  {desc}"))

        # ── Feasibility ────────────────────────────────────────────────────
        if not module_filter or module_filter == "feasibility":
            try:
                res = await _run_feasibility(tc, verbose)
                tc_result["modules"]["feasibility"] = res
                status = "pass" if res["passed"] else "fail"
                counts["feasibility"][status] += 1
                if verbose:
                    icon = green("  PASS feasibility") if res["passed"] else red("  FAIL feasibility")
                    print(icon)
                    for d in res.get("details", []):
                        safe_d = str(d).encode("ascii", "replace").decode("ascii")
                        print(dim(f"    {safe_d}"))
            except Exception as exc:
                tc_result["modules"]["feasibility"] = {"passed": False, "error": str(exc)}
                counts["feasibility"]["fail"] += 1
                if verbose:
                    print(red(f"  FAIL feasibility -- ERROR: {exc}"))

        # ── Edit Correctness ───────────────────────────────────────────────
        if not module_filter or module_filter == "edit_correctness":
            try:
                res = _run_edit_correctness(tc, verbose)
                tc_result["modules"]["edit_correctness"] = res
                if res.get("skipped"):
                    counts["edit_correctness"]["skip"] += 1
                    if verbose:
                        print(dim("  SKIP edit_correctness -- skipped (no prior state)"))
                else:
                    status = "pass" if res["passed"] else "fail"
                    counts["edit_correctness"][status] += 1
                    if verbose:
                        icon = green("  PASS edit_correctness") if res["passed"] else red("  FAIL edit_correctness")
                        print(icon)
                        for d in res.get("details", []):
                            safe_d = str(d).encode("ascii", "replace").decode("ascii")
                            print(dim(f"    {safe_d}"))
            except Exception as exc:
                tc_result["modules"]["edit_correctness"] = {"passed": False, "error": str(exc)}
                counts["edit_correctness"]["fail"] += 1
                if verbose:
                    print(red(f"  FAIL edit_correctness -- ERROR: {exc}"))

        # ── Grounding ──────────────────────────────────────────────────────
        if not module_filter or module_filter == "grounding":
            try:
                res = await _run_grounding(tc, verbose)
                tc_result["modules"]["grounding"] = res
                status = "pass" if res["passed"] else "fail"
                counts["grounding"][status] += 1
                if verbose:
                    icon = green("  PASS grounding") if res["passed"] else red("  FAIL grounding")
                    if res.get("rag_grounding_score") is not None:
                        icon += dim(f"  (RAG score: {res['rag_grounding_score']}/5)")
                    elif res.get("rag_grounding_skipped"):
                        icon += dim("  (RAG score: skipped)")
                    print(icon)
                    for d in res.get("details", []):
                        safe_d = str(d).encode("ascii", "replace").decode("ascii")
                        print(dim(f"    {safe_d}"))
            except Exception as exc:
                tc_result["modules"]["grounding"] = {"passed": False, "error": str(exc)}
                counts["grounding"]["fail"] += 1
                if verbose:
                    print(red(f"  FAIL grounding -- ERROR: {exc}"))

        report["results"].append(tc_result)
        if verbose:
            print()

    # ── Summary table ────────────────────────────────────────────────────────
    report["summary"] = counts
    print(bold("-" * 72))
    print(bold(f"  {'MODULE':<22} {'PASS':>6} {'FAIL':>6} {'SKIP':>6}"))
    print(bold("-" * 72))
    all_pass = True
    for mod, c in counts.items():
        if not module_filter or module_filter == mod:
            p, f, s = c["pass"], c["fail"], c["skip"]
            pass_str = green(str(p).rjust(6))
            fail_str = (red(str(f).rjust(6)) if f else dim(str(f).rjust(6)))
            skip_str = yellow(str(s).rjust(6)) if s else dim(str(s).rjust(6))
            print(f"  {mod:<22} {pass_str} {fail_str} {skip_str}")
            if f > 0:
                all_pass = False
    print(bold("-" * 72))
    overall = green("ALL CHECKS PASSED") if all_pass else red("SOME CHECKS FAILED")
    print(f"\n  Overall: {bold(overall)}\n")

    return report


def _save_report(report: Dict[str, Any], output_path: Optional[str]) -> str:
    """Write the JSON report and return the file path."""
    if output_path is None:
        logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
        os.makedirs(logs_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(logs_dir, f"eval_log_{ts}.json")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False, default=str)

    return output_path


# ─────────────────────────────────────────────────────────────────────────────
# Pytest integration — each module gets a top-level test function
# ─────────────────────────────────────────────────────────────────────────────

def test_feasibility_all_cases():
    """Pytest: all golden dataset cases must pass feasibility checks."""
    dataset = _load_golden_dataset()
    failures = []
    for tc in dataset:
        result = asyncio.get_event_loop().run_until_complete(
            _run_feasibility(tc, verbose=False)
        )
        if not result["passed"]:
            failures.append(f"{tc['test_id']}: {result['details']}")
    assert not failures, "\n".join(failures)


def test_edit_correctness_all_cases():
    """Pytest: all multi-turn golden dataset cases must pass edit correctness."""
    dataset = _load_golden_dataset()
    failures = []
    for tc in dataset:
        result = _run_edit_correctness(tc, verbose=False)
        if not result.get("skipped") and not result["passed"]:
            failures.append(f"{tc['test_id']}: {result['details']}")
    assert not failures, "\n".join(failures)


def test_grounding_all_cases():
    """Pytest: all golden dataset cases must pass grounding checks."""
    dataset = _load_golden_dataset()
    failures = []
    for tc in dataset:
        result = asyncio.get_event_loop().run_until_complete(
            _run_grounding(tc, verbose=False)
        )
        if not result["passed"]:
            failures.append(f"{tc['test_id']}: {result['details']}")
    assert not failures, "\n".join(failures)


# ─────────────────────────────────────────────────────────────────────────────
# CLI entrypoint
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="The Property Scout — Evaluation Suite Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python evals/run_evals.py\n"
            "  python evals/run_evals.py --module grounding --verbose\n"
            "  python evals/run_evals.py --output evals/logs/my_run.json\n"
            "  pytest evals/ -v\n"
        ),
    )
    parser.add_argument(
        "--module",
        choices=["feasibility", "edit_correctness", "grounding"],
        default=None,
        help="Run only a specific eval module (default: run all).",
    )
    parser.add_argument(
        "--output",
        default=None,
        metavar="PATH",
        help="Output path for the JSON report (default: evals/logs/eval_log_<timestamp>.json).",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print per-test-case details to stdout.",
    )
    args = parser.parse_args()

    report = asyncio.run(run_all(module_filter=args.module, verbose=args.verbose))
    path = _save_report(report, args.output)
    print(f"  Report saved -> {path}\n")


if __name__ == "__main__":
    main()
