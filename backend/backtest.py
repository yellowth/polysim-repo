"""
Backtesting engine — validate Polysim predictions against real election results.

Supports GE2020 and GE2025. Compares predicted incumbent (PAP) support %
against actual vote share per constituency.
"""
import asyncio
from real_data import load_ge_results, get_enriched_grc_profiles, _normalize_constituency, _match_constituency
from demographics import build_personas
from mock_mode import mock_agent_response
from contagion_v2 import propagate_sentiment_v2
from market import compute_agent_bet, compute_market_price


def run_backtest(ge_year: int = 2025, use_mock: bool = True, target_agents: int = 200) -> dict:
    """
    Run simulation for each GRC and compare against actual election results.

    Args:
        ge_year: election year to backtest against (2020 or 2025)
        use_mock: use mock responses (True) or real OpenAI calls (False)
        target_agents: number of personas to generate

    Returns: {
        constituencies: [{name, predicted, actual, error, correct_call, market_price}],
        summary: {mae, correlation, call_accuracy_pct, market_price},
        price_history: [{round, market_price}]
    }
    """
    ge_results = load_ge_results(ge_year)
    profiles = get_enriched_grc_profiles(ge_year)
    personas = build_personas(target_count=target_agents)

    # Build actual PAP vote % lookup
    actual_pap = {}
    for constituency, parties in ge_results.items():
        pap_entry = next((p for p in parties if p["party"] == "PAP"), None)
        if pap_entry:
            actual_pap[_normalize_constituency(constituency)] = pap_entry["vote_percentage"] * 100

    # Run simulation
    if use_mock:
        results = [mock_agent_response(p) for p in personas]
    else:
        # Real mode — run async agent simulation
        from agent_engine import run_simulation
        from mock_mode import mock_parse_provisions
        provisions = mock_parse_provisions("")
        results = asyncio.get_event_loop().run_until_complete(
            run_simulation(personas, provisions)
        )

    # Compute initial market bets
    for r in results:
        compute_agent_bet(r)
    initial_market = compute_market_price(results)

    # Apply contagion (3 rounds) — track price history
    price_history = [{
        "round": 0,
        "label": "Initial bets",
        "market_price": initial_market["market_price"],
        "implied_probability_pct": initial_market["implied_probability_pct"],
    }]

    for rnd in range(3):
        results = propagate_sentiment_v2(results, rnd)
        mp = compute_market_price(results)
        price_history.append({
            "round": rnd + 1,
            "label": f"Market round {rnd + 1}",
            "market_price": mp["market_price"],
            "implied_probability_pct": mp["implied_probability_pct"],
        })

    # Aggregate by GRC using weighted support
    grc_support = {}
    for r in results:
        grc = r["persona"]["grc"]
        if grc not in grc_support:
            grc_support[grc] = {"support_w": 0, "total_w": 0, "yes_bets": 0, "total_bets": 0}
        weight = r["persona"].get("weight", 1)
        if r["sentiment"] == "support":
            grc_support[grc]["support_w"] += weight
        grc_support[grc]["total_w"] += weight
        grc_support[grc]["yes_bets"] += r.get("yes_bet", 0)
        grc_support[grc]["total_bets"] += r.get("yes_bet", 0) + r.get("no_bet", 0)

    # Compare predictions against actuals
    comparisons = []
    errors = []
    correct = 0
    total = 0

    for grc_name in profiles:
        short = _normalize_constituency(grc_name)
        # Try direct match first, then fuzzy
        actual = actual_pap.get(short)
        if actual is None:
            matched_key = _match_constituency(grc_name, {k: None for k in actual_pap})
            if matched_key:
                actual = actual_pap.get(_normalize_constituency(matched_key))

        predicted_data = grc_support.get(grc_name)
        if actual is None or predicted_data is None:
            continue

        predicted_pct = (predicted_data["support_w"] / predicted_data["total_w"] * 100) \
            if predicted_data["total_w"] > 0 else 50.0
        market_price = (predicted_data["yes_bets"] / predicted_data["total_bets"]) \
            if predicted_data["total_bets"] > 0 else 0.5

        error = predicted_pct - actual
        abs_error = abs(error)
        errors.append(abs_error)

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
            "market_price": round(market_price, 4),
        })

    comparisons.sort(key=lambda x: x["abs_error"])

    # Pearson correlation
    correlation = 0.0
    if len(comparisons) > 1:
        pred = [c["predicted_support_pct"] for c in comparisons]
        act = [c["actual_pap_pct"] for c in comparisons]
        mean_p = sum(pred) / len(pred)
        mean_a = sum(act) / len(act)
        cov = sum((p - mean_p) * (a - mean_a) for p, a in zip(pred, act))
        std_p = (sum((p - mean_p) ** 2 for p in pred)) ** 0.5
        std_a = (sum((a - mean_a) ** 2 for a in act)) ** 0.5
        correlation = cov / (std_p * std_a) if std_p * std_a > 0 else 0

    mae = sum(errors) / len(errors) if errors else 0
    final_market = compute_market_price(results)

    return {
        "ge_year": ge_year,
        "constituencies": comparisons,
        "summary": {
            "mae": round(mae, 1),
            "max_error": round(max(errors), 1) if errors else 0,
            "min_error": round(min(errors), 1) if errors else 0,
            "correct_calls": correct,
            "total": total,
            "call_accuracy_pct": round(correct / total * 100, 1) if total > 0 else 0,
            "correlation": round(correlation, 3),
            "market_price": final_market["market_price"],
            "implied_probability_pct": final_market["implied_probability_pct"],
            "confidence_level": final_market["confidence_level"],
            "total_agents": len(personas),
        },
        "price_history": price_history,
    }


if __name__ == "__main__":
    import sys
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2025
    result = run_backtest(ge_year=year, use_mock=True, target_agents=200)

    print(f"=== Polysim GE{year} Backtest ===\n")
    print(f"Agents: {result['summary']['total_agents']}")
    print(f"MAE: {result['summary']['mae']}%")
    print(f"Max error: {result['summary']['max_error']}%")
    print(f"Correct calls: {result['summary']['correct_calls']}/{result['summary']['total']} "
          f"({result['summary']['call_accuracy_pct']}%)")
    print(f"Correlation: {result['summary']['correlation']}")
    print(f"Market price: {result['summary']['market_price']} "
          f"({result['summary']['implied_probability_pct']}% implied)")
    print(f"Confidence: {result['summary']['confidence_level']}")

    print(f"\nPrice history:")
    for ph in result["price_history"]:
        print(f"  {ph['label']}: {ph['market_price']:.4f} ({ph['implied_probability_pct']}%)")

    print(f"\nPer-constituency:")
    for c in result["constituencies"]:
        marker = "+" if c["correct_call"] else "x"
        print(f"  {marker} {c['constituency']:35s} predicted={c['predicted_support_pct']:5.1f}%  "
              f"actual={c['actual_pap_pct']:5.1f}%  error={c['error']:+5.1f}%  "
              f"mkt={c['market_price']:.3f}")
