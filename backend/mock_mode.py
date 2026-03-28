"""
Mock mode for testing without OpenAI/TinyFish API keys.
Provides deterministic fake responses that match the real data shapes.
Covers all 4 age bands × 4 races with risk_appetite and conviction_bet.
"""
import random
import hashlib


def _seed(persona: dict) -> int:
    key = f"{persona.get('race','')}-{persona.get('age','')}-{persona.get('grc','')}-{persona.get('income','')}"
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


# Base sentiment weights: (race, age) -> probability distribution
# Calibrated against GE2020 incumbent support patterns:
# - Working-age Chinese show moderate support (national avg ~61% PAP)
# - Malay population shows higher support for welfare/housing (PAP base)
# - Young voters (21-29) are more critical and less decided
# - Seniors (60+) trend more supportive of incumbent
SENTIMENT_WEIGHTS = {
    # Chinese
    ("Chinese", "21-29"): {"support": 0.40, "neutral": 0.30, "reject": 0.30},
    ("Chinese", "30-44"): {"support": 0.55, "neutral": 0.25, "reject": 0.20},
    ("Chinese", "45-59"): {"support": 0.60, "neutral": 0.22, "reject": 0.18},
    ("Chinese", "60+"):   {"support": 0.68, "neutral": 0.18, "reject": 0.14},
    # Malay
    ("Malay", "21-29"):   {"support": 0.55, "neutral": 0.25, "reject": 0.20},
    ("Malay", "30-44"):   {"support": 0.65, "neutral": 0.20, "reject": 0.15},
    ("Malay", "45-59"):   {"support": 0.70, "neutral": 0.18, "reject": 0.12},
    ("Malay", "60+"):     {"support": 0.75, "neutral": 0.15, "reject": 0.10},
    # Indian
    ("Indian", "21-29"):  {"support": 0.38, "neutral": 0.32, "reject": 0.30},
    ("Indian", "30-44"):  {"support": 0.50, "neutral": 0.28, "reject": 0.22},
    ("Indian", "45-59"):  {"support": 0.55, "neutral": 0.25, "reject": 0.20},
    ("Indian", "60+"):    {"support": 0.62, "neutral": 0.23, "reject": 0.15},
    # Others
    ("Others", "21-29"):  {"support": 0.35, "neutral": 0.35, "reject": 0.30},
    ("Others", "30-44"):  {"support": 0.45, "neutral": 0.30, "reject": 0.25},
    ("Others", "45-59"):  {"support": 0.50, "neutral": 0.28, "reject": 0.22},
    ("Others", "60+"):    {"support": 0.55, "neutral": 0.28, "reject": 0.17},
}

REASONS = {
    # Chinese
    ("support", "Chinese", "21-29"): "The housing grant expansion really helps lah. My friends all saving for BTO, this makes it more reachable.",
    ("reject", "Chinese", "21-29"): "All these grants don't help if BTO queue still 5 years. Address supply first lah.",
    ("neutral", "Chinese", "21-29"): "Some of these OK, but I care more about job market and career growth tbh.",
    ("support", "Chinese", "30-44"): "With young kids the housing grant and transport freeze really help our monthly budget.",
    ("reject", "Chinese", "30-44"): "Income threshold too low sia. $9K household income means dual-income couples all kena excluded.",
    ("neutral", "Chinese", "30-44"): "Some of these help, some don't really affect me. Transport fare freeze is nice though.",
    ("support", "Chinese", "45-59"): "SkillsFuture boost good for mid-career switch. Industry changing so fast, need more training support.",
    ("reject", "Chinese", "45-59"): "These measures feel like election goodies. What about long-term structural issues like healthcare costs?",
    ("neutral", "Chinese", "45-59"): "Appreciate the effort but these don't address my main concern — retirement adequacy.",
    ("support", "Chinese", "60+"): "The Silver Support increase very good. Every bit helps with groceries and medical costs.",
    ("reject", "Chinese", "60+"): "20% increase still not enough lah. Medicine costs go up more than that every year.",
    ("neutral", "Chinese", "60+"): "Got some help here and there but still worry about hospital bills.",
    # Malay
    ("support", "Malay", "21-29"): "Wah the EHG increase damn good news. Finally can think about getting own place without stress.",
    ("reject", "Malay", "21-29"): "Why SkillsFuture credit only go to bosses? Workers also need help with retraining costs.",
    ("neutral", "Malay", "21-29"): "Some ok lah but I'm more worried about getting a good job first before thinking about housing.",
    ("support", "Malay", "30-44"): "Housing grant and GST voucher really help families like mine. Cost of living crazy now.",
    ("reject", "Malay", "30-44"): "These measures short-term only. Need more education subsidies for our children.",
    ("neutral", "Malay", "30-44"): "Appreciate the housing help but childcare costs still killing us every month.",
    ("support", "Malay", "45-59"): "Good to see the government addressing cost of living. The transport freeze helps a lot.",
    ("reject", "Malay", "45-59"): "Still waiting for real structural help for the community. These are band-aids only.",
    ("neutral", "Malay", "45-59"): "Some measures ok but nothing addressing employment discrimination concerns.",
    ("support", "Malay", "60+"): "Alhamdulillah, the GST Voucher and Silver Support really help. Cost of living so high.",
    ("reject", "Malay", "60+"): "Need more help for elderly who don't have CPF savings. 20% not enough.",
    ("neutral", "Malay", "60+"): "Some help here and there lah but still struggling with medical bills.",
    # Indian
    ("support", "Indian", "21-29"): "SkillsFuture boost great for tech career. More certifications = better job prospects.",
    ("reject", "Indian", "21-29"): "These measures are all short-term populist moves. What about foreign talent competition?",
    ("neutral", "Indian", "21-29"): "Mixed feelings. Some good for workers but doesn't address integration issues.",
    ("support", "Indian", "30-44"): "SkillsFuture boost is great for the tech industry. More training subsidies means better skills.",
    ("reject", "Indian", "30-44"): "These measures are all short-term. What about long-term structural changes for cost of living?",
    ("neutral", "Indian", "30-44"): "Some good measures but nothing transformative. Still waiting for real wage growth policies.",
    ("support", "Indian", "45-59"): "The transport fare freeze and Silver Support are practical moves that help immediately.",
    ("reject", "Indian", "45-59"): "More needs to be done for healthcare. Medishield premiums keep going up.",
    ("neutral", "Indian", "45-59"): "Decent policies overall but nothing that changes the fundamental cost structure.",
    ("support", "Indian", "60+"): "Good that they increase Silver Support. Many of our elderly really need the extra help.",
    ("reject", "Indian", "60+"): "Still not enough support for elderly without family. Need better social safety net.",
    ("neutral", "Indian", "60+"): "Some help is better than no help, but the core issues remain unaddressed.",
    # Others
    ("support", "Others", "21-29"): "Transport fare freeze is practical. At least one less thing to worry about.",
    ("reject", "Others", "21-29"): "None of these address the real issues — PR/citizenship pathways and work visa uncertainty.",
    ("neutral", "Others", "21-29"): "Some measures ok but most don't apply to my situation directly.",
    ("support", "Others", "30-44"): "Housing grant expansion helps those of us who finally got PR. Every dollar counts.",
    ("reject", "Others", "30-44"): "These policies still don't address fundamental integration and employment challenges.",
    ("neutral", "Others", "30-44"): "Appreciate some of the measures but still feel like outsider looking in.",
    ("support", "Others", "45-59"): "SkillsFuture credit boost good for my business. Can send more staff for training.",
    ("reject", "Others", "45-59"): "After so many years here, still feel these policies don't consider non-Chinese minorities enough.",
    ("neutral", "Others", "45-59"): "Some useful measures but the bigger picture of inclusion hasn't changed.",
    ("support", "Others", "60+"): "Silver Support increase welcome. Healthcare costs are the biggest worry.",
    ("reject", "Others", "60+"): "Need better integration support for elderly from minority communities.",
    ("neutral", "Others", "60+"): "Not bad lah, but most of these don't really apply to my situation.",
}


def mock_agent_response(persona: dict) -> dict:
    """Generate a deterministic mock agent response with market model fields."""
    rng = random.Random(_seed(persona))
    key = (persona.get("race", "Chinese"), persona.get("age", "30-44"))
    weights = SENTIMENT_WEIGHTS.get(key, {"support": 0.5, "neutral": 0.3, "reject": 0.2})

    sentiment = rng.choices(
        ["support", "neutral", "reject"],
        weights=[weights["support"], weights["neutral"], weights["reject"]],
        k=1
    )[0]

    vote_map = {"support": "for", "neutral": "undecided", "reject": "against"}
    confidence = round(rng.uniform(0.45, 0.95), 2)

    reason_key = (sentiment, persona.get("race", "Chinese"), persona.get("age", "30-44"))
    reason = REASONS.get(
        reason_key,
        f"As a {persona.get('age', '')} {persona.get('race', '')} in {persona.get('grc', '')}, I feel {sentiment} about this policy."
    )

    score_map = {"support": 1.0, "neutral": 0.0, "reject": -1.0}
    risk_appetite = persona.get("risk_appetite", 0.5)

    return {
        "sentiment": sentiment,
        "confidence": confidence,
        "reason": reason,
        "vote_intent": vote_map[sentiment],
        "key_provision": f"#{rng.randint(1, 5)}",
        "persona": persona,
        "score": score_map[sentiment],
        "risk_appetite": risk_appetite,
    }
