"""
Mock mode for testing without OpenAI/TinyFish API keys.
Provides deterministic fake responses that match the real data shapes.
"""
import random
import hashlib

# Deterministic seed based on persona for consistent results
def _seed(persona: dict) -> int:
    key = f"{persona.get('race','')}-{persona.get('age','')}-{persona.get('grc','')}"
    return int(hashlib.md5(key.encode()).hexdigest()[:8], 16)


def mock_parse_provisions(text: str) -> list[dict]:
    """Return fake but realistic SG policy provisions."""
    return [
        {
            "id": 1,
            "title": "Enhanced Housing Grant Expansion",
            "summary": "Increase the Enhanced CPF Housing Grant (EHG) ceiling from $80,000 to $120,000 for first-time buyers with household income up to $9,000/month.",
            "affected_groups": ["young couples", "first-time buyers", "lower-income"],
            "parameters": {"income_threshold": 9000, "grant_amount": 120000}
        },
        {
            "id": 2,
            "title": "GST Voucher Top-Up",
            "summary": "One-off $500 GST Voucher cash payout for Singaporean adults in HDB 1-3 room flats with assessed income below $34,000.",
            "affected_groups": ["elderly", "lower-income", "HDB residents"],
            "parameters": {"payout_amount": 500, "income_ceiling": 34000}
        },
        {
            "id": 3,
            "title": "SkillsFuture Enterprise Credit Boost",
            "summary": "Double the SkillsFuture Enterprise Credit from $10,000 to $20,000 for SMEs to subsidize employee training.",
            "affected_groups": ["PMEs", "SME owners", "working adults"],
            "parameters": {"credit_amount": 20000}
        },
        {
            "id": 4,
            "title": "Silver Support Scheme Enhancement",
            "summary": "Increase Silver Support quarterly payouts by 20% for seniors aged 65+ with limited CPF savings and no property.",
            "affected_groups": ["elderly", "retirees", "lower-income seniors"],
            "parameters": {"increase_pct": 20, "age_threshold": 65}
        },
        {
            "id": 5,
            "title": "Public Transport Fare Freeze",
            "summary": "Freeze public transport fares for 12 months despite rising energy costs, absorb difference through government subsidy.",
            "affected_groups": ["commuters", "students", "lower-income"],
            "parameters": {"freeze_months": 12}
        }
    ]


SENTIMENT_WEIGHTS = {
    # (race, age) -> base sentiment tendency for housing/welfare policies
    ("Chinese", "30-44"): {"support": 0.55, "neutral": 0.25, "reject": 0.20},
    ("Chinese", "60+"): {"support": 0.65, "neutral": 0.20, "reject": 0.15},
    ("Malay", "30-44"): {"support": 0.70, "neutral": 0.20, "reject": 0.10},
    ("Malay", "60+"): {"support": 0.75, "neutral": 0.15, "reject": 0.10},
    ("Indian", "30-44"): {"support": 0.50, "neutral": 0.30, "reject": 0.20},
    ("Indian", "60+"): {"support": 0.60, "neutral": 0.25, "reject": 0.15},
    ("Others", "30-44"): {"support": 0.45, "neutral": 0.35, "reject": 0.20},
    ("Others", "60+"): {"support": 0.55, "neutral": 0.30, "reject": 0.15},
}

REASONS = {
    ("support", "Chinese", "30-44"): "The housing grant expansion really helps lah, my wife and I still saving for BTO. Finally can afford Punggol.",
    ("support", "Chinese", "60+"): "The Silver Support increase very good. Every bit helps with groceries and medical costs.",
    ("reject", "Chinese", "30-44"): "Income threshold too low sia. $9K household income means dual-income couples all kena excluded.",
    ("neutral", "Chinese", "30-44"): "Some of these help, some don't really affect me. Transport fare freeze is nice though.",
    ("support", "Malay", "30-44"): "Wah the EHG increase is damn good news for us. Housing prices crazy now, this really helps young families.",
    ("support", "Malay", "60+"): "Alhamdulillah, the GST Voucher and Silver Support really help. Cost of living so high these days.",
    ("reject", "Malay", "30-44"): "Why the SkillsFuture credit only go to SME bosses? What about the workers who need retraining?",
    ("neutral", "Malay", "60+"): "Some help here and there lah but still struggling with medical bills. Need more support.",
    ("support", "Indian", "30-44"): "SkillsFuture boost is great for the tech industry. More companies might sponsor certifications now.",
    ("support", "Indian", "60+"): "Good that they increase Silver Support. Many of our elderly really need the extra help.",
    ("reject", "Indian", "30-44"): "These measures are all short-term. What about long-term structural changes for cost of living?",
    ("neutral", "Indian", "30-44"): "Some good measures but nothing transformative. Still waiting for real wage growth policies.",
    ("support", "Others", "30-44"): "Transport fare freeze is practical. At least one less thing to worry about this year.",
    ("neutral", "Others", "60+"): "Not bad lah, but most of these don't really apply to my situation.",
    ("reject", "Others", "30-44"): "None of these address the real issues — PR/citizenship pathways and integration support.",
}


def mock_agent_response(persona: dict) -> dict:
    """Generate a deterministic mock agent response."""
    rng = random.Random(_seed(persona))
    key = (persona.get("race", "Chinese"), persona.get("age", "30-44"))
    weights = SENTIMENT_WEIGHTS.get(key, {"support": 0.5, "neutral": 0.3, "reject": 0.2})

    sentiment = rng.choices(
        ["support", "neutral", "reject"],
        weights=[weights["support"], weights["neutral"], weights["reject"]],
        k=1
    )[0]

    vote_map = {"support": "for", "neutral": "undecided", "reject": "against"}
    confidence = rng.uniform(0.5, 0.95)

    reason_key = (sentiment, persona.get("race", "Chinese"), persona.get("age", "30-44"))
    reason = REASONS.get(reason_key, f"As a {persona['age']} {persona['race']} in {persona['grc']}, I feel {sentiment} about this policy.")

    score_map = {"support": 1.0, "neutral": 0.0, "reject": -1.0}

    return {
        "sentiment": sentiment,
        "confidence": round(confidence, 2),
        "reason": reason,
        "vote_intent": vote_map[sentiment],
        "key_provision": f"#{rng.randint(1, 5)}",
        "persona": persona,
        "score": score_map[sentiment],
    }
