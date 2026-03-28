"""Build agent personas from demographic data — region-configurable, scalable."""
import json
import os
import random
import hashlib
from config import get_config


def load_grc_profiles() -> dict:
    """Load constituency demographic profiles from data dir."""
    cfg = get_config()
    path = os.path.join(os.path.dirname(__file__), "..", "data", cfg["profiles_file"])
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def _compute_risk_appetite(age: str, income_tier: str, housing: str) -> float:
    """
    Derive risk appetite (0.0–1.0) from demographics.
    Younger + richer + better housing = more risk tolerant.
    Weighted: age 40%, income 35%, housing 25%.
    """
    cfg = get_config()
    age_r = cfg["risk_appetite_by_age"].get(age, 0.5)
    inc_r = cfg["risk_appetite_by_income"].get(income_tier, 0.5)
    hou_r = cfg["risk_appetite_by_housing"].get(housing, 0.5)
    return round(0.40 * age_r + 0.35 * inc_r + 0.25 * hou_r, 3)


def build_personas(target_count: int = 100) -> list[dict]:
    """
    Build representative agent personas weighted to real demographics.

    Generates personas across ALL 4 age bands, with income and housing
    diversity drawn from Census distributions. Each persona carries a
    population weight for representative aggregation.

    Args:
        target_count: target number of personas (scales up for more fidelity)
    """
    cfg = get_config()
    grcs = load_grc_profiles()
    if not grcs:
        return []

    races = cfg["races"]
    age_bands = cfg["age_bands"]
    age_weights = cfg["age_band_weights"]
    income_tiers = cfg["income_tiers"]
    income_dist_by_age = cfg["income_distribution_by_age"]
    housing_dist_by_income = cfg["housing_distribution_by_income"]
    occupations = cfg["occupations"]
    concerns = cfg["concerns"]
    family_status = cfg["family_status_by_age"]

    personas = []
    total_pop = sum(p.get("pop", 0) for p in grcs.values())

    for grc_name, profile in grcs.items():
        grc_pop = profile.get("pop", 0)
        # How many personas this GRC should contribute (proportional to population)
        grc_budget = max(1, round(target_count * grc_pop / total_pop)) if total_pop > 0 else 1

        for race in races:
            race_pct = profile.get(race.lower(), 0.03)
            if race_pct < 0.02:
                continue  # skip negligible segments

            for age in age_bands:
                age_w = age_weights.get(age, 0.25)
                # How many personas for this GRC × race × age
                segment_share = race_pct * age_w
                # Ensure at least 1 for significant segments
                n_personas = max(1, round(grc_budget * segment_share))
                if segment_share < 0.005:
                    continue

                # Determine income/housing mix for this segment
                inc_dist = income_dist_by_age.get(age, {"middle": 1.0})

                for i in range(n_personas):
                    # Deterministic selection seeded on segment
                    seed_key = f"{grc_name}-{race}-{age}-{i}"
                    seed_val = int(hashlib.md5(seed_key.encode()).hexdigest()[:8], 16)
                    rng = random.Random(seed_val)

                    # Pick income tier from distribution
                    tier_labels = list(inc_dist.keys())
                    tier_weights = [inc_dist[t] for t in tier_labels]
                    chosen_tier = rng.choices(tier_labels, weights=tier_weights, k=1)[0]

                    # Find income label for this tier
                    tier_info = next((t for t in income_tiers if t["tier"] == chosen_tier), income_tiers[1])
                    income_label = tier_info["label"]

                    # Pick housing from income-based distribution
                    housing_dist = housing_dist_by_income.get(chosen_tier, {"HDB 4-5 Room": 1.0})
                    housing_labels = list(housing_dist.keys())
                    housing_weights = [housing_dist[h] for h in housing_labels]
                    chosen_housing = rng.choices(housing_labels, weights=housing_weights, k=1)[0]

                    # Pick occupation deterministically
                    occ_list = occupations.get(chosen_tier, ["worker"])
                    occupation = occ_list[seed_val % len(occ_list)]

                    # Population weight for this persona
                    weight = round(grc_pop * race_pct * age_w / max(n_personas, 1))

                    # Risk appetite for prediction market model
                    risk_appetite = _compute_risk_appetite(age, chosen_tier, chosen_housing)

                    # Pick 3 concerns for this race
                    race_concerns = concerns.get(race, ["cost of living"])
                    selected_concerns = rng.sample(race_concerns, min(3, len(race_concerns)))

                    persona = {
                        "age": age,
                        "race": race,
                        "income": income_label,
                        "income_tier": chosen_tier,
                        "housing": chosen_housing,
                        "grc": grc_name,
                        "occupation": occupation,
                        "family_status": family_status.get(age, ""),
                        "concerns": ", ".join(selected_concerns),
                        "weight": max(weight, 1),
                        "risk_appetite": risk_appetite,
                    }
                    personas.append(persona)

    # If we overshot, trim while preserving GRC coverage (every GRC keeps >= 1 agent).
    # First guarantee one representative per GRC, then fill remaining quota by weight.
    if len(personas) > target_count * 1.5:
        target = int(target_count * 1.2)

        # Group by GRC
        by_grc = {}
        for p in personas:
            by_grc.setdefault(p["grc"], []).append(p)

        # Phase 1: pick the highest-weight persona from each GRC as a guaranteed seat
        guaranteed = []
        remainder = []
        for grc_personas in by_grc.values():
            grc_personas.sort(key=lambda p: p["weight"], reverse=True)
            guaranteed.append(grc_personas[0])
            remainder.extend(grc_personas[1:])

        # Phase 2: fill remaining slots from the rest, sorted by weight descending
        slots_left = max(0, target - len(guaranteed))
        remainder.sort(key=lambda p: p["weight"], reverse=True)
        personas = guaranteed + remainder[:slots_left]

    return personas
