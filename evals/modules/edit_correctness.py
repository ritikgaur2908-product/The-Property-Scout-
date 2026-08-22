from typing import Dict, Any, List

def evaluate_edit_correctness(
    previous_state: Dict[str, Any],
    new_state: Dict[str, Any],
    expected_state: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Evaluates state tracking edit correctness.
    Ensures that the targeted keys correctly changed to match expected_state,
    and all untargeted keys remain strictly identical to previous_state.
    """
    results = {
        "passed": True,
        "details": []
    }

    # Keys that are expected to change or remain the same according to expected_state
    for key, expected_val in expected_state.items():
        if key not in new_state and expected_val is not None:
            results["passed"] = False
            results["details"].append(f"Expected key '{key}' missing from new_state")
        elif new_state.get(key) != expected_val:
            results["passed"] = False
            results["details"].append(f"Key '{key}' is {new_state.get(key)}, expected {expected_val}")

    # Untargeted keys (keys in previous_state that are not explicitly updated in expected_state)
    for key, prev_val in previous_state.items():
        if key not in expected_state:
            if key not in new_state:
                results["passed"] = False
                results["details"].append(f"Untargeted key '{key}' was dropped")
            elif new_state.get(key) != prev_val:
                results["passed"] = False
                results["details"].append(f"Untargeted key '{key}' mutated from {prev_val} to {new_state.get(key)}")

    return results
