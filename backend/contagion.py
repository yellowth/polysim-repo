"""Simple social contagion model — weighted neighbor influence."""

def get_influence_weight(agent_a: dict, agent_b: dict) -> float:
    """Calculate influence weight between two agents."""
    pa, pb = agent_a["persona"], agent_b["persona"]
    weight = 0.0

    # Same race, adjacent age = strong family/community tie
    if pa["race"] == pb["race"]:
        weight += 0.15
        age_diff = abs(_age_mid(pa["age"]) - _age_mid(pb["age"]))
        if age_diff <= 15:
            weight += 0.10  # family-like bond

    # Same GRC = neighborhood effect
    if pa["grc"] == pb["grc"]:
        weight += 0.10

    # Same housing = class effect
    if pa["housing"] == pb["housing"]:
        weight += 0.08

    # Social media exposure (younger = more influenced)
    social_media = {"21-29": 0.12, "30-44": 0.08, "45-59": 0.04, "60+": 0.02}
    weight += social_media.get(pa["age"], 0.05)

    return min(weight, 0.4)  # cap total influence

def propagate_sentiment(results: list[dict], round_num: int) -> list[dict]:
    """One round of sentiment propagation across all agents."""
    new_results = []
    for agent in results:
        # Calculate weighted average of neighbors
        total_influence = 0.0
        weighted_score = 0.0
        for other in results:
            if other["persona"]["grc"] == agent["persona"]["grc"] or \
               other["persona"]["race"] == agent["persona"]["race"]:
                w = get_influence_weight(agent, other)
                weighted_score += w * other["score"]
                total_influence += w

        if total_influence > 0:
            neighbor_avg = weighted_score / total_influence
            # Blend own score with neighbor influence
            damping = 0.7  # own opinion weight
            new_score = damping * agent["score"] + (1 - damping) * neighbor_avg
        else:
            new_score = agent["score"]

        updated = {**agent}
        updated["score"] = new_score
        updated["sentiment"] = _score_to_label(new_score)
        updated["contagion_round"] = round_num
        new_results.append(updated)
    return new_results

def _score_to_label(score: float) -> str:
    if score > 0.33:
        return "support"
    elif score < -0.33:
        return "reject"
    return "neutral"

def _age_mid(age_band: str) -> int:
    mapping = {"21-29": 25, "30-44": 37, "45-59": 52, "60+": 68}
    return mapping.get(age_band, 40)
