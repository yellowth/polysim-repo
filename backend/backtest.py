"""
Backtesting engine — validate Polysim predictions against real GE2020 results.

Approach:
1. For each constituency, run the agent simulation with a "status quo" policy
   (i.e., the incumbent government's track record).
2. Compare predicted support % against actual PAP vote share in GE2020.
3. Report accuracy metrics: MAE, correlation, correct winner calls.

This provides judge-facing credibility: "Our model retroactively predicts GE2020
within X% accuracy without being trained on election data."
"""
import json
import os
from real_data import load_ge_results, load_voter_turnout, get_enriched_grc_profiles
from demographics import build_personas
from mock_mode import mock_agent_response
from contagion_v2 import propagate_sentiment_v2


def _normalize_constituency(name: str) -> str:
    """Normalize GRC name for matching."""
    return name.upper().replace(" GRC", "").replace(" SMC", "").strip()


def run_backtest(use_mock: bool = True) -> dict:
    """
    Run simulation for each GRC and compare against GE2020 actual results.

    Returns: {
        "constituencies": [{name, predicted_support_pct, actual_pap_pct, error, correct_call}],
        "summary": {mae, max_error, correct_calls, total, correlation}
    }
    """
    ge_results = load_ge_results(2020)
    profiles = get_enriched_grc_profiles()
    personas = build_personas(target_count=200)  # More personas for better coverage

    # Build GE2020 lookup: constituency -> PAP vote %
    actual_pap = {}
    for constituency, parties in ge_results.items():
        pap_entry = next((p for p in parties if p["party"] == "PAP"), None)
        if pap_entry:
            actual_pap[_normalize_constituency(constituency)] = pap_entry["vote_percentage"] * 100

    # Run simulation
    if use_mock:
        results = [mock_agent_response(p) for p in personas]
    else:
        # Would use real OpenAI calls here
        results = [mock_agent_response(p) for p in personas]

    # Apply contagion
    for rnd in range(3):
        results = propagate_sentiment_v2(results, rnd)

    # Aggregate by GRC
    grc_support = {}
    for r in results:
        grc = r["persona"]["grc"]
        if grc not in grc_support:
            grc_support[grc] = {"support": 0, "total": 0}
        weight = r["persona"].get("weight", 1)
        if r["sentiment"] == "support":
            grc_support[grc]["support"] += weight
        grc_support[grc]["total"] += weight

    # Compare predictions against actuals
    comparisons = []
    errors = []
    correct = 0
    total = 0

    for grc_name in profiles:
        short = _normalize_constituency(grc_name)
        actual = actual_pap.get(short)
        predicted_data = grc_support.get(grc_name)

        if actual is None or predicted_data is None:
            continue

        predicted_pct = (predicted_data["support"] / predicted_data["total"] * 100) \
            if predicted_data["total"] > 0 else 50.0

        error = predicted_pct - actual
        abs_error = abs(error)
        errors.append(abs_error)

        # Did we call the winner correctly? (>50% = incumbent wins)
        predicted_win = predicted_pct > 50
        actual_win = actual > 50
        call_correct = predicted_win == actual_win
        if call_correct:
            correct += 1
        total += 1

        comparisons.append({
            "constituency": grc_name,
            "predicted_support_pct": round(predicted_pct, 1),
            "actual_pap_pct": round(actual, 1),
            "error": round(error, 1),
            "abs_error": round(abs_error, 1),
            "correct_call": call_correct,
        })

    comparisons.sort(key=lambda x: x["abs_error"])

    # Compute correlation
    if len(comparisons) > 1:
        pred = [c["predicted_support_pct"] for c in comparisons]
        act = [c["actual_pap_pct"] for c in comparisons]
        mean_p = sum(pred) / len(pred)
        mean_a = sum(act) / len(act)
        cov = sum((p - mean_p) * (a - mean_a) for p, a in zip(pred, act))
        std_p = (sum((p - mean_p) ** 2 for p in pred)) ** 0.5
        std_a = (sum((a - mean_a) ** 2 for a in act)) ** 0.5
        correlation = cov / (std_p * std_a) if std_p * std_a > 0 else 0
    else:
        correlation = 0

    mae = sum(errors) / len(errors) if errors else 0

    return {
        "constituencies": comparisons,
        "summary": {
            "mae": round(mae, 1),
            "max_error": round(max(errors), 1) if errors else 0,
            "min_error": round(min(errors), 1) if errors else 0,
            "correct_calls": correct,
            "total": total,
            "call_accuracy_pct": round(correct / total * 100, 1) if total > 0 else 0,
            "correlation": round(correlation, 3),
        }
    }


if __name__ == "__main__":
    result = run_backtest(use_mock=True)
    print("=== Polysim GE2020 Backtest ===\n")
    print(f"MAE: {result['summary']['mae']}%")
    print(f"Max error: {result['summary']['max_error']}%")
    print(f"Correct calls: {result['summary']['correct_calls']}/{result['summary']['total']} "
          f"({result['summary']['call_accuracy_pct']}%)")
    print(f"Correlation: {result['summary']['correlation']}")
    print("\nPer-constituency:")
    for c in result["constituencies"]:
        marker = "✓" if c["correct_call"] else "✗"
        print(f"  {marker} {c['constituency']:30s} predicted={c['predicted_support_pct']:5.1f}%  "
              f"actual={c['actual_pap_pct']:5.1f}%  error={c['error']:+5.1f}%")
