"""
Prediction Market Model — transforms polling into a market mechanism.

Each agent is a self-interested bettor. Instead of just stating sentiment,
agents place conviction-weighted bets on policy outcomes using virtual utility
tokens. The market-clearing price represents the implied probability of the
policy passing — more reliable than raw polling because it weights conviction
and skin-in-the-game.

Key concepts:
- risk_appetite (0-1): derived from demographics (age, income, housing)
- conviction_bet: virtual tokens wagered = risk_appetite × confidence × weight
- market_price: Σ(YES bets) / Σ(all bets) — implied probability of PASS
- Each contagion round is a "market round" where information propagates
  and agents can update their positions
"""


def compute_agent_bet(agent: dict) -> dict:
    """
    Compute the conviction bet for a single agent.

    An agent's bet size scales with:
    - risk_appetite: willingness to commit (from demographics)
    - confidence: how sure they are (from LLM evaluation)
    - weight: population segment they represent

    Returns the agent dict enriched with bet fields.
    """
    risk = agent.get("risk_appetite", agent.get("persona", {}).get("risk_appetite", 0.5))
    confidence = agent.get("confidence", 0.5)
    weight = agent.get("persona", {}).get("weight", 1)

    # Bet size: how many tokens this agent puts on the table
    bet_size = risk * confidence * weight

    # Direction: support → YES (policy passes), reject → NO, neutral → split
    sentiment = agent.get("sentiment", "neutral")
    if sentiment == "support":
        yes_bet = bet_size
        no_bet = 0.0
    elif sentiment == "reject":
        yes_bet = 0.0
        no_bet = bet_size
    else:
        # Neutral agents split weakly — slight lean toward status quo (NO)
        yes_bet = bet_size * 0.4
        no_bet = bet_size * 0.6

    agent["conviction_bet"] = round(bet_size, 2)
    agent["yes_bet"] = round(yes_bet, 2)
    agent["no_bet"] = round(no_bet, 2)
    return agent


def compute_market_price(results: list[dict]) -> dict:
    """
    Compute the market-clearing price from all agent bets.

    Market price = total YES bets / (total YES + total NO bets)
    This is the implied probability of the policy passing.

    Also computes:
    - volume: total tokens in the market
    - spread: difference between highest YES bettor confidence and lowest
    - liquidity: number of agents with non-trivial bets
    """
    total_yes = 0.0
    total_no = 0.0
    confidences = []
    active_bettors = 0

    for agent in results:
        # Ensure bets are computed
        if "yes_bet" not in agent:
            compute_agent_bet(agent)

        total_yes += agent.get("yes_bet", 0)
        total_no += agent.get("no_bet", 0)
        if agent.get("conviction_bet", 0) > 0:
            active_bettors += 1
            confidences.append(agent.get("confidence", 0.5))

    total_volume = total_yes + total_no
    market_price = total_yes / total_volume if total_volume > 0 else 0.5

    spread = (max(confidences) - min(confidences)) if confidences else 0

    return {
        "market_price": round(market_price, 4),
        "implied_probability_pct": round(market_price * 100, 1),
        "total_volume": round(total_volume, 0),
        "yes_volume": round(total_yes, 0),
        "no_volume": round(total_no, 0),
        "active_bettors": active_bettors,
        "spread": round(spread, 3),
        "call": "PASS" if market_price > 0.5 else "FAIL",
        "confidence_level": _confidence_label(market_price),
    }


def compute_market_by_grc(results: list[dict]) -> dict:
    """Compute per-GRC market prices for geographic breakdown."""
    grc_bets = {}
    for agent in results:
        if "yes_bet" not in agent:
            compute_agent_bet(agent)
        grc = agent.get("persona", {}).get("grc", "Unknown")
        if grc not in grc_bets:
            grc_bets[grc] = {"yes": 0.0, "no": 0.0, "agents": []}
        grc_bets[grc]["yes"] += agent.get("yes_bet", 0)
        grc_bets[grc]["no"] += agent.get("no_bet", 0)
        grc_bets[grc]["agents"].append(agent)

    result = {}
    for grc, data in grc_bets.items():
        total = data["yes"] + data["no"]
        price = data["yes"] / total if total > 0 else 0.5
        result[grc] = {
            "market_price": round(price, 4),
            "implied_probability_pct": round(price * 100, 1),
            "yes_volume": round(data["yes"], 0),
            "no_volume": round(data["no"], 0),
            "total_volume": round(total, 0),
            "agents": data["agents"],
        }
    return result


def compute_price_history(initial_results: list[dict], contagion_rounds: list[list[dict]]) -> list[dict]:
    """
    Build a price history from initial agent results + each contagion round.
    Returns a list of {round, market_price, yes_volume, no_volume} entries
    suitable for charting.
    """
    history = []

    # Round 0: initial agent bets (pre-contagion)
    for agent in initial_results:
        compute_agent_bet(agent)
    mp = compute_market_price(initial_results)
    history.append({
        "round": 0,
        "label": "Initial bets",
        "market_price": mp["market_price"],
        "implied_probability_pct": mp["implied_probability_pct"],
        "yes_volume": mp["yes_volume"],
        "no_volume": mp["no_volume"],
    })

    # Rounds 1-N: after each contagion round
    for i, round_results in enumerate(contagion_rounds):
        for agent in round_results:
            compute_agent_bet(agent)
        mp = compute_market_price(round_results)
        history.append({
            "round": i + 1,
            "label": f"Market round {i + 1}",
            "market_price": mp["market_price"],
            "implied_probability_pct": mp["implied_probability_pct"],
            "yes_volume": mp["yes_volume"],
            "no_volume": mp["no_volume"],
        })

    return history


def adjust_with_live_sentiment(market_price: float, live_sentiments: list[dict]) -> float:
    """
    Adjust market price using live-scraped sentiment data (from TinyFish).

    Live sentiment acts as an external signal — like real trades entering
    the prediction market from outside.

    Each live sentiment contributes a small adjustment based on its
    engagement level (more engagement = more market impact).
    """
    if not live_sentiments:
        return market_price

    total_engagement = 0
    weighted_signal = 0.0

    for s in live_sentiments:
        engagement = s.get("engagement", 1)
        total_engagement += engagement
        sentiment = s.get("sentiment", "neutral")
        if sentiment == "positive":
            weighted_signal += engagement * 1.0
        elif sentiment == "negative":
            weighted_signal += engagement * -1.0
        # neutral contributes 0

    if total_engagement == 0:
        return market_price

    # Normalize to [-1, 1]
    signal = weighted_signal / total_engagement

    # Live data gets 15% influence on market price (external information)
    # This represents the "wisdom of crowds" beyond our simulated agents
    LIVE_WEIGHT = 0.15
    adjusted = (1 - LIVE_WEIGHT) * market_price + LIVE_WEIGHT * ((signal + 1) / 2)

    return round(max(0.01, min(0.99, adjusted)), 4)


def _confidence_label(price: float) -> str:
    """Human-readable confidence based on how far price is from 0.5."""
    distance = abs(price - 0.5)
    if distance > 0.30:
        return "very high"
    elif distance > 0.20:
        return "high"
    elif distance > 0.10:
        return "moderate"
    elif distance > 0.05:
        return "low"
    return "toss-up"
