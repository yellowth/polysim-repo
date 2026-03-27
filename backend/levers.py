"""Policy lever adjustments for interactive re-simulation."""
import copy

LEVER_DEFINITIONS = {
    "income_threshold": {
        "label": "Income Eligibility Threshold",
        "min": 2000, "max": 15000, "step": 500, "default": 5000,
        "unit": "SGD/month",
        "description": "Maximum household income to qualify"
    },
    "subsidy_amount": {
        "label": "Subsidy / Grant Amount",
        "min": 0, "max": 50000, "step": 5000, "default": 10000,
        "unit": "SGD",
        "description": "Direct subsidy amount per eligible household"
    },
    "rollout_months": {
        "label": "Implementation Timeline",
        "min": 3, "max": 36, "step": 3, "default": 12,
        "unit": "months",
        "description": "Months until full rollout"
    }
}

def apply_lever(provisions: list[dict], lever: str, value: float) -> list[dict]:
    """Modify provisions based on lever adjustment."""
    modified = copy.deepcopy(provisions)

    if lever == "income_threshold":
        for p in modified:
            if "income" in p.get("title", "").lower() or "eligib" in p.get("summary", "").lower():
                p["summary"] = p["summary"] + f" [ADJUSTED: income threshold set to ${int(value)}/month]"
                p["parameters"] = p.get("parameters", {})
                p["parameters"]["income_threshold"] = value

    elif lever == "subsidy_amount":
        for p in modified:
            if any(kw in p.get("summary", "").lower() for kw in ["grant", "subsid", "support", "amount"]):
                p["summary"] = p["summary"] + f" [ADJUSTED: grant amount set to ${int(value)}]"
                p["parameters"] = p.get("parameters", {})
                p["parameters"]["subsidy_amount"] = value

    elif lever == "rollout_months":
        for p in modified:
            p["summary"] = p["summary"] + f" [ADJUSTED: rollout in {int(value)} months]"
            p["parameters"] = p.get("parameters", {})
            p["parameters"]["rollout_months"] = value

    return modified

def get_lever_definitions() -> dict:
    return LEVER_DEFINITIONS
