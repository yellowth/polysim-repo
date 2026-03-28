"""
Contagion Model v2 — Optimized social influence propagation.

## Design Analysis & Decision

### Problem
v1 iterates all agents × all agents (O(n²)) per round. With 40 agents this is
1600 comparisons × 3 rounds = 4800 — fine. But scaling to 200+ agents makes it
slow (40K+ comparisons per round), and 1000 agents is unacceptable (3M+).

### Alternatives Considered

1. **Pre-computed adjacency matrix (O(n²) setup, O(n×k) per round)**
   - Build influence weight matrix once upfront, then multiply.
   - Pro: Amortizes the pairwise cost. Matrix operations can use numpy.
   - Con: Still O(n²) memory. Marginal improvement for our scale.

2. **Group-based propagation (O(g² + n×g) where g = number of groups)**
   - Instead of agent-to-agent, compute *group averages* first (by GRC, race,
     housing, age), then propagate group→agent.
   - Pro: Dramatically fewer operations. 15 GRCs × 4 races × 4 ages = ~240 groups
     max, but in practice ~40-80 active groups. Per round: compute group means
     (O(n)), then update each agent from its group memberships (O(n×g_memberships)).
   - Con: Loses individual agent-to-agent nuance.
   - **THIS IS THE WINNER for our use case.**

3. **Spatial indexing / KD-tree**
   - Build a feature-space KD-tree, only propagate to k-nearest neighbors.
   - Pro: True O(n×k×log(n)) per round.
   - Con: Over-engineered for demographics. Features are categorical, not spatial.
     Would need embeddings first. Overkill.

4. **Graph-based with networkx**
   - Build explicit social graph, use graph diffusion.
   - Pro: Elegant, extensible.
   - Con: Another dependency. Graph construction is still O(n²).

### Decision: Group-based propagation (Option 2)

Best fit because:
- Our influence model already uses categorical group membership (same race, same GRC,
  same housing, same age band) — it's naturally group-based.
- O(n) per round instead of O(n²).
- Preserves the "ripple effect" visual (group shifts cascade round-by-round).
- Easy to extend with "social media" as a cross-cutting group.
- Individual agent scores still evolve uniquely (each agent has a different mix of
  group memberships with different weights).
"""

from collections import defaultdict


# Influence weights by group type
GROUP_WEIGHTS = {
    "grc": 0.10,           # neighborhood effect
    "race": 0.15,          # ethnic community ties
    "race_age": 0.10,      # family-like bonds (same race + adjacent age)
    "housing": 0.08,       # class solidarity
    "social_media": None,   # varies by age (see below)
}

SOCIAL_MEDIA_BY_AGE = {
    "21-29": 0.12,
    "30-44": 0.08,
    "45-59": 0.04,
    "60+": 0.02,
}

# Damping factor: how much an agent weights their own opinion vs group influence
# Higher = more stubborn / less influenced
DAMPING = 0.7


def _compute_group_means(results: list[dict]) -> dict:
    """
    Compute mean sentiment score for each group.
    Returns: {group_key: {"mean": float, "count": int}}
    """
    groups = defaultdict(lambda: {"sum": 0.0, "count": 0})

    for r in results:
        p = r["persona"]
        score = r["score"]

        # GRC group
        groups[("grc", p["grc"])]["sum"] += score
        groups[("grc", p["grc"])]["count"] += 1

        # Race group
        groups[("race", p["race"])]["sum"] += score
        groups[("race", p["race"])]["count"] += 1

        # Race × Age group (family/community bonds)
        groups[("race_age", p["race"], p["age"])]["sum"] += score
        groups[("race_age", p["race"], p["age"])]["count"] += 1

        # Housing group
        groups[("housing", p["housing"])]["sum"] += score
        groups[("housing", p["housing"])]["count"] += 1

    # Convert sums to means
    for key, data in groups.items():
        data["mean"] = data["sum"] / data["count"] if data["count"] > 0 else 0.0

    return groups


def _compute_agent_influence(persona: dict, group_means: dict) -> tuple[float, float]:
    """
    Compute the weighted neighbor influence for one agent from group means.
    Returns: (weighted_score, total_weight)
    """
    weighted_score = 0.0
    total_weight = 0.0

    # GRC influence
    grc_key = ("grc", persona["grc"])
    if grc_key in group_means:
        w = GROUP_WEIGHTS["grc"]
        weighted_score += w * group_means[grc_key]["mean"]
        total_weight += w

    # Race influence
    race_key = ("race", persona["race"])
    if race_key in group_means:
        w = GROUP_WEIGHTS["race"]
        weighted_score += w * group_means[race_key]["mean"]
        total_weight += w

    # Race × Age influence (stronger bond for same race + similar age)
    race_age_key = ("race_age", persona["race"], persona["age"])
    if race_age_key in group_means:
        w = GROUP_WEIGHTS["race_age"]
        weighted_score += w * group_means[race_age_key]["mean"]
        total_weight += w

    # Housing influence
    housing_key = ("housing", persona["housing"])
    if housing_key in group_means:
        w = GROUP_WEIGHTS["housing"]
        weighted_score += w * group_means[housing_key]["mean"]
        total_weight += w

    # Social media broadcast effect (age-dependent)
    social_w = SOCIAL_MEDIA_BY_AGE.get(persona["age"], 0.05)
    # Social media = exposure to OVERALL population sentiment (global mean)
    global_key = ("grc", persona["grc"])  # Use GRC as proxy for local social sphere
    if global_key in group_means:
        weighted_score += social_w * group_means[global_key]["mean"]
        total_weight += social_w

    return weighted_score, total_weight


def propagate_sentiment_v2(results: list[dict], round_num: int) -> list[dict]:
    """
    One round of group-based sentiment propagation.

    Complexity: O(n) to compute group means + O(n × g) to update agents
    where g = number of group memberships per agent (~5).
    Total: O(n) per round vs O(n²) in v1.
    """
    # Step 1: Compute group means (O(n))
    group_means = _compute_group_means(results)

    # Step 2: Update each agent based on group influences (O(n × 5))
    new_results = []
    for agent in results:
        weighted_score, total_weight = _compute_agent_influence(
            agent["persona"], group_means
        )

        if total_weight > 0:
            neighbor_avg = weighted_score / total_weight
            new_score = DAMPING * agent["score"] + (1 - DAMPING) * neighbor_avg
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
