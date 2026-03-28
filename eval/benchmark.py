"""Benchmark script for evaluating Polisim simulation accuracy."""
import json, asyncio, sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from demographics import build_personas
from agent_engine import run_simulation
from contagion import propagate_sentiment


SAMPLE_PROVISIONS = [
    {
        "id": 1,
        "title": "GST Voucher Enhancement",
        "summary": "Increase GST Voucher cash payout from $500 to $700 for households with income below $3,000/month",
        "affected_groups": ["low-income", "elderly"],
        "parameters": {"income_threshold": 3000, "amount": 700}
    },
    {
        "id": 2,
        "title": "HDB BTO Price Adjustment",
        "summary": "Reduce BTO flat prices by 5% for first-time buyers under age 35",
        "affected_groups": ["young adults", "first-time buyers"],
        "parameters": {"discount_pct": 5, "age_cap": 35}
    },
    {
        "id": 3,
        "title": "Foreign Worker Levy Increase",
        "summary": "Increase foreign worker levy by 15% for S-Pass holders in services sector",
        "affected_groups": ["employers", "SMEs", "service sector"],
        "parameters": {"levy_increase_pct": 15}
    }
]


async def run_benchmark():
    print("Building personas...")
    personas = build_personas(target_count=20)
    print(f"  {len(personas)} personas created")

    print("\nRunning simulation...")
    results = await run_simulation(personas, SAMPLE_PROVISIONS)
    print(f"  {len(results)} agent results collected")

    # Analyze results
    sentiments = {"support": 0, "neutral": 0, "reject": 0}
    for r in results:
        sentiments[r["sentiment"]] = sentiments.get(r["sentiment"], 0) + 1

    print("\nPre-contagion sentiment:")
    for s, count in sentiments.items():
        print(f"  {s}: {count} ({count/len(results)*100:.1f}%)")

    # Run contagion
    for round_num in range(3):
        results = propagate_sentiment(results, round_num)

    sentiments_post = {"support": 0, "neutral": 0, "reject": 0}
    for r in results:
        sentiments_post[r["sentiment"]] = sentiments_post.get(r["sentiment"], 0) + 1

    print("\nPost-contagion sentiment (3 rounds):")
    for s, count in sentiments_post.items():
        print(f"  {s}: {count} ({count/len(results)*100:.1f}%)")

    print("\nBenchmark complete.")


if __name__ == "__main__":
    asyncio.run(run_benchmark())
