"""
Polisim benchmark/eval script.
Validates simulation output quality against known priors.
Supports both file-based eval and live pipeline eval.
"""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


def validate_demographic_differentiation(results: list) -> dict:
    """Check that different demographics show differentiated sentiment."""
    by_race = {}
    by_age = {}
    for r in results:
        race = r["persona"]["race"]
        age = r["persona"]["age"]
        score = r.get("score", 0)

        by_race.setdefault(race, []).append(score)
        by_age.setdefault(age, []).append(score)

    race_means = {r: sum(s)/len(s) for r, s in by_race.items() if s}
    age_means = {a: sum(s)/len(s) for a, s in by_age.items() if s}

    race_variance = (max(race_means.values()) - min(race_means.values())) if race_means else 0
    age_variance = (max(age_means.values()) - min(age_means.values())) if age_means else 0

    return {
        "by_race": {r: round(v, 3) for r, v in race_means.items()},
        "by_age": {a: round(v, 3) for a, v in age_means.items()},
        "race_variance": round(race_variance, 3),
        "age_variance": round(age_variance, 3),
        "race_differentiated": race_variance > 0.05,
        "age_differentiated": age_variance > 0.05,
        "num_races": len(race_means),
        "num_ages": len(age_means),
    }


def validate_vote_coherence(vote_prediction: dict) -> dict:
    """Check vote totals sum to 100%."""
    total = vote_prediction.get("for_pct", 0) + \
            vote_prediction.get("against_pct", 0) + \
            vote_prediction.get("undecided_pct", 0)
    return {
        "total_pct": round(total, 1),
        "coherent": abs(total - 100) < 1.0
    }


def validate_market_model(results: list) -> dict:
    """Check that market model produces reasonable prices."""
    from market import compute_agent_bet, compute_market_price

    for r in results:
        if "yes_bet" not in r:
            compute_agent_bet(r)

    mp = compute_market_price(results)
    return {
        "market_price": mp["market_price"],
        "implied_probability_pct": mp["implied_probability_pct"],
        "total_volume": mp["total_volume"],
        "active_bettors": mp["active_bettors"],
        "spread": mp["spread"],
        "valid_price": 0.01 < mp["market_price"] < 0.99,
        "sufficient_volume": mp["total_volume"] > 0,
        "sufficient_bettors": mp["active_bettors"] >= 5,
    }


def validate_backtest_accuracy(ge_year: int = 2025) -> dict:
    """Run backtest and check accuracy metrics."""
    from backtest import run_backtest

    result = run_backtest(ge_year=ge_year, use_mock=True, target_agents=200)
    s = result["summary"]

    return {
        "ge_year": ge_year,
        "mae": s["mae"],
        "correct_calls": s["correct_calls"],
        "total": s["total"],
        "call_accuracy_pct": s["call_accuracy_pct"],
        "correlation": s["correlation"],
        "market_price": s["market_price"],
        "acceptable_mae": s["mae"] < 25,
        "acceptable_calls": s["call_accuracy_pct"] > 50,
    }


def run_eval(results_file: str = None):
    """Run all validation checks."""
    print("=== Polisim Eval ===\n")

    if results_file:
        with open(results_file) as f:
            data = json.load(f)
        results = data.get("agent_results", [])
        vote = data.get("vote_prediction", {})
    else:
        # Live pipeline eval
        from demographics import build_personas
        from mock_mode import mock_agent_response
        from contagion_v2 import propagate_sentiment_v2
        from main import compute_vote_prediction

        personas = build_personas(target_count=100)
        results = [mock_agent_response(p) for p in personas]
        for rnd in range(3):
            results = propagate_sentiment_v2(results, rnd)
        vote = compute_vote_prediction(results)

    print(f"Total agents: {len(results)}")

    # 1. Demographic differentiation
    diff = validate_demographic_differentiation(results)
    print(f"\n1. Demographic Differentiation")
    print(f"   Races: {diff['num_races']} | Race spread: {diff['race_variance']:.3f} {'PASS' if diff['race_differentiated'] else 'FAIL'}")
    print(f"   Ages:  {diff['num_ages']} | Age spread:  {diff['age_variance']:.3f} {'PASS' if diff['age_differentiated'] else 'FAIL'}")
    for race, score in diff["by_race"].items():
        print(f"     {race}: {score:+.3f}")
    for age, score in diff["by_age"].items():
        print(f"     {age}: {score:+.3f}")

    # 2. Vote coherence
    if vote:
        coherence = validate_vote_coherence(vote)
        print(f"\n2. Vote Coherence: {'PASS' if coherence['coherent'] else 'FAIL'}")
        print(f"   For: {vote.get('for_pct')}% | Against: {vote.get('against_pct')}% | Undecided: {vote.get('undecided_pct')}%")
        print(f"   Call: {vote.get('call')}")

    # 3. Market model
    mkt = validate_market_model(results)
    print(f"\n3. Market Model")
    print(f"   Price: {mkt['market_price']:.4f} ({mkt['implied_probability_pct']}%)")
    print(f"   Volume: {mkt['total_volume']:.0f} | Bettors: {mkt['active_bettors']}")
    print(f"   Valid: {'PASS' if mkt['valid_price'] and mkt['sufficient_volume'] and mkt['sufficient_bettors'] else 'FAIL'}")

    # 4. Backtest (GE2025)
    print(f"\n4. Backtest GE2025")
    bt = validate_backtest_accuracy(2025)
    print(f"   MAE: {bt['mae']}% {'PASS' if bt['acceptable_mae'] else 'FAIL'}")
    print(f"   Correct calls: {bt['correct_calls']}/{bt['total']} ({bt['call_accuracy_pct']}%) {'PASS' if bt['acceptable_calls'] else 'FAIL'}")
    print(f"   Correlation: {bt['correlation']}")
    print(f"   Market price: {bt['market_price']:.4f}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_eval(sys.argv[1])
    else:
        run_eval()
