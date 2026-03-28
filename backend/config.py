"""
Region configuration module — extensible for different geographies.

To simulate a different region:
1. Create a new config dict following the SINGAPORE structure
2. Place your GRC/constituency profiles JSON in /data/
3. Set ACTIVE_REGION to your config
"""

SINGAPORE = {
    "name": "Singapore",
    "currency": "SGD",
    "races": ["Chinese", "Malay", "Indian", "Others"],
    "age_bands": ["21-29", "30-44", "45-59", "60+"],
    "income_tiers": [
        {"label": "<$3K", "tier": "low", "range": (0, 3000)},
        {"label": "$3K-$8K", "tier": "middle", "range": (3000, 8000)},
        {"label": "$8K-$15K", "tier": "upper-middle", "range": (8000, 15000)},
        {"label": ">$15K", "tier": "high", "range": (15000, 50000)},
    ],
    "housing_types": ["HDB 1-3 Room", "HDB 4-5 Room", "Condo/EC", "Landed"],
    "occupations": {
        "low": ["hawker stall assistant", "delivery rider", "cleaner", "security guard",
                "production operator", "bus driver", "retail cashier", "kitchen helper"],
        "middle": ["admin executive", "nurse", "technician", "sales associate",
                   "logistics coordinator", "dental assistant", "insurance agent", "police officer"],
        "upper-middle": ["PME engineer", "teacher", "bank relationship manager", "SME owner",
                         "accountant", "physiotherapist", "marketing manager", "architect"],
        "high": ["senior director", "doctor", "lawyer", "tech lead",
                 "investment banker", "surgeon", "management consultant", "fund manager"],
    },
    "concerns": {
        "Chinese": ["cost of living", "education", "property prices", "CPF", "job security", "healthcare costs"],
        "Malay": ["cost of living", "education subsidies", "employment opportunities", "housing", "skills training", "childcare"],
        "Indian": ["employment", "integration", "education", "healthcare", "foreign worker policies", "cost of living"],
        "Others": ["PR/citizenship", "cost of living", "employment", "integration", "healthcare", "education"],
    },
    "family_status_by_age": {
        "21-29": "single, living with parents",
        "30-44": "married with young children",
        "45-59": "married with teenage/adult children",
        "60+": "retired or semi-retired, grandchildren",
    },
    # Risk appetite base values by demographic factor (for prediction market model)
    "risk_appetite_by_age": {"21-29": 0.75, "30-44": 0.65, "45-59": 0.50, "60+": 0.35},
    "risk_appetite_by_income": {"low": 0.30, "middle": 0.50, "upper-middle": 0.70, "high": 0.85},
    "risk_appetite_by_housing": {
        "HDB 1-3 Room": 0.25, "HDB 4-5 Room": 0.45,
        "Condo/EC": 0.70, "Landed": 0.85,
    },
    # Income tier distribution by age band (from Census 2020 approximation)
    "income_distribution_by_age": {
        "21-29": {"low": 0.35, "middle": 0.45, "upper-middle": 0.15, "high": 0.05},
        "30-44": {"low": 0.15, "middle": 0.40, "upper-middle": 0.30, "high": 0.15},
        "45-59": {"low": 0.20, "middle": 0.35, "upper-middle": 0.25, "high": 0.20},
        "60+": {"low": 0.45, "middle": 0.35, "upper-middle": 0.15, "high": 0.05},
    },
    # Housing distribution by income tier
    "housing_distribution_by_income": {
        "low": {"HDB 1-3 Room": 0.60, "HDB 4-5 Room": 0.35, "Condo/EC": 0.04, "Landed": 0.01},
        "middle": {"HDB 1-3 Room": 0.15, "HDB 4-5 Room": 0.65, "Condo/EC": 0.15, "Landed": 0.05},
        "upper-middle": {"HDB 1-3 Room": 0.05, "HDB 4-5 Room": 0.35, "Condo/EC": 0.45, "Landed": 0.15},
        "high": {"HDB 1-3 Room": 0.02, "HDB 4-5 Room": 0.10, "Condo/EC": 0.45, "Landed": 0.43},
    },
    # Age band distribution weights (from Census 2020)
    "age_band_weights": {"21-29": 0.18, "30-44": 0.28, "45-59": 0.26, "60+": 0.28},
    # Constituency data file
    "profiles_file": "grc_profiles.json",
    "demographics_file": "sg_demographics.json",
    "ge_results_file": "ge_results.csv",
    # Contagion model parameters
    "contagion": {
        "damping": 0.70,
        "rounds": 3,
        "group_weights": {
            "grc": 0.10,
            "race": 0.15,
            "race_age": 0.10,
            "housing": 0.08,
        },
        "social_media_by_age": {
            "21-29": 0.12,
            "30-44": 0.08,
            "45-59": 0.04,
            "60+": 0.02,
        },
    },
}

# Active region — change this to switch geographies
ACTIVE_REGION = SINGAPORE


def get_config() -> dict:
    """Return the active region configuration."""
    return ACTIVE_REGION
