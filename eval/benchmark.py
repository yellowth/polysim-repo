"""
Polisim benchmark/eval script.
Validates simulation output quality against known priors.
"""
import json
import sys

def validate_demographic_differentiation(results: list) -> dict:
    """Check that different demographics show differentiated sentiment."""
    by_race = {}
    for r in results:
        race = r["persona"]["race"]
        if race not in by_race:
            by_race[race] = {"support": 0, "total": 0}
        score_map = {"support": 1, "neutral": 0, "reject": -1}
        by_race[race]["support"] += score_map.get(r["sentiment"], 0)
        by_race[race]["total"] += 1

    sentiments = {
        race: data["support"] / data["total"]
        for race, data in by_race.items()
        if data["total"] > 0
    }

    variance = max(sentiments.values()) - min(sentiments.values()) if sentiments else 0
    return {
        "by_race": sentiments,
        "variance": variance,
        "differentiated": variance > 0.1,  # at least 10% spread
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


def run_eval(results_file: str):
    """Load results JSON and run all checks."""
    with open(results_file) as f:
        data = json.load(f)

    results = data.get("agent_results", [])
    vote = data.get("vote_prediction", {})

    print("=== Polisim Eval ===")
    print(f"Total agents: {len(results)}")

    diff = validate_demographic_differentiation(results)
    print(f"\nDemographic differentiation: {'PASS' if diff['differentiated'] else 'FAIL'}")
    print(f"  Variance: {diff['variance']:.2f}")
    for race, score in diff["by_race"].items():
        print(f"  {race}: {score:.2f}")

    if vote:
        coherence = validate_vote_coherence(vote)
        print(f"\nVote coherence: {'PASS' if coherence['coherent'] else 'FAIL'}")
        print(f"  For: {vote.get('for_pct')}% | Against: {vote.get('against_pct')}% | Undecided: {vote.get('undecided_pct')}%")
        print(f"  Call: {vote.get('call')}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python benchmark.py <results.json>")
        sys.exit(1)
    run_eval(sys.argv[1])
