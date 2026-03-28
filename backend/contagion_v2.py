"""
Contagion Model v2 — Group-based social influence propagation, O(n) per round.

Design: Instead of O(n²) pairwise agent comparison, compute group means first
(by GRC, race, race×age, housing), then blend each agent's score with their
group influences. Each agent has a unique mix of group memberships, so
individual scores still diverge.

In the prediction market framing, each contagion round is a "market round"
where information cascades through social networks, shifting agents' positions.
"""

from collections import defaultdict
from config import get_config
from market import compute_agent_bet


def _get_contagion_config():
    """Load contagion parameters from active region config."""
    cfg = get_config()
    return cfg.get("contagion", {})


def _compute_group_means(results: list[dict]) -> dict:
    """
    Compute weighted mean sentiment score for each group.
    Weights agents by their population weight for representative means.
    Returns: {group_key: {"mean": float, "count": int, "weighted_sum": float}}
    """
    groups = defaultdict(lambda: {"weighted_sum": 0.0, "total_weight": 0.0, "count": 0})

    for r in results:
        p = r["persona"]
        score = r["score"]
        weight = p.get("weight", 1)

        # GRC group
        key = ("grc", p["grc"])
        groups[key]["weighted_sum"] += score * weight
        groups[key]["total_weight"] += weight
        groups[key]["count"] += 1

        # Race group
        key = ("race", p["race"])
        groups[key]["weighted_sum"] += score * weight
        groups[key]["total_weight"] += weight
        groups[key]["count"] += 1

        # Race × Age group (family/community bonds)
        key = ("race_age", p["race"], p["age"])
        groups[key]["weighted_sum"] += score * weight
        groups[key]["total_weight"] += weight
        groups[key]["count"] += 1

        # Housing group
        key = ("housing", p["housing"])
        groups[key]["weighted_sum"] += score * weight
        groups[key]["total_weight"] += weight
        groups[key]["count"] += 1

    # Compute weighted means
    for data in groups.values():
        data["mean"] = data["weighted_sum"] / data["total_weight"] if data["total_weight"] > 0 else 0.0

    return groups


def _compute_global_mean(results: list[dict]) -> float:
    """Compute population-weighted global mean sentiment."""
    total_weighted = 0.0
    total_weight = 0.0
    for r in results:
        w = r["persona"].get("weight", 1)
        total_weighted += r["score"] * w
        total_weight += w
    return total_weighted / total_weight if total_weight > 0 else 0.0


def _compute_agent_influence(persona: dict, group_means: dict, global_mean: float) -> tuple[float, float]:
    """
    Compute the weighted neighbor influence for one agent from group means.
    Returns: (weighted_score, total_weight)
    """
    contagion_cfg = _get_contagion_config()
    group_weights = contagion_cfg.get("group_weights", {})
    social_media_by_age = contagion_cfg.get("social_media_by_age", {})

    weighted_score = 0.0
    total_weight = 0.0

    # GRC influence (neighborhood effect)
    grc_key = ("grc", persona["grc"])
    if grc_key in group_means:
        w = group_weights.get("grc", 0.10)
        weighted_score += w * group_means[grc_key]["mean"]
        total_weight += w

    # Race influence (ethnic community ties)
    race_key = ("race", persona["race"])
    if race_key in group_means:
        w = group_weights.get("race", 0.15)
        weighted_score += w * group_means[race_key]["mean"]
        total_weight += w

    # Race × Age influence (family-like bonds)
    race_age_key = ("race_age", persona["race"], persona["age"])
    if race_age_key in group_means:
        w = group_weights.get("race_age", 0.10)
        weighted_score += w * group_means[race_age_key]["mean"]
        total_weight += w

    # Housing influence (class solidarity)
    housing_key = ("housing", persona["housing"])
    if housing_key in group_means:
        w = group_weights.get("housing", 0.08)
        weighted_score += w * group_means[housing_key]["mean"]
        total_weight += w

    # Social media broadcast effect — uses GLOBAL mean (cross-GRC information flow)
    social_w = social_media_by_age.get(persona["age"], 0.05)
    weighted_score += social_w * global_mean
    total_weight += social_w

    return weighted_score, total_weight


def propagate_sentiment_v2(results: list[dict], round_num: int) -> list[dict]:
    """
    One round of group-based sentiment propagation.

    After propagation, recalculates market bets (conviction_bet) so the
    market price evolves naturally with sentiment shifts.
    """
    contagion_cfg = _get_contagion_config()
    damping = contagion_cfg.get("damping", 0.70)

    # Step 1: Compute group means (O(n))
    group_means = _compute_group_means(results)
    global_mean = _compute_global_mean(results)

    # Step 2: Update each agent based on group influences (O(n × 5))
    new_results = []
    for agent in results:
        weighted_score, total_weight = _compute_agent_influence(
            agent["persona"], group_means, global_mean
        )

        if total_weight > 0:
            neighbor_avg = weighted_score / total_weight
            new_score = damping * agent["score"] + (1 - damping) * neighbor_avg
        else:
            new_score = agent["score"]

        updated = {**agent}
        updated["score"] = new_score
        updated["sentiment"] = _score_to_label(new_score)
        updated["contagion_round"] = round_num

        # Update vote_intent to match new sentiment
        if updated["sentiment"] == "support":
            updated["vote_intent"] = "for"
        elif updated["sentiment"] == "reject":
            updated["vote_intent"] = "against"
        else:
            updated["vote_intent"] = "undecided"

        # Recalculate market bet with new sentiment/score
        # Confidence adjusts slightly with social proof (capped to prevent runaway)
        base_conf = updated.get("confidence", 0.5)
        social_boost = min(0.05, abs(neighbor_avg) * 0.03 * (round_num + 1))
        updated["confidence"] = min(0.95, base_conf + social_boost)
        compute_agent_bet(updated)

        new_results.append(updated)

    return new_results


def _score_to_label(score: float) -> str:
    if score > 0.33:
        return "support"
    elif score < -0.33:
        return "reject"
    return "neutral"
