"""Build agent personas from Singapore demographic data."""
import json, os

# Singapore demographic segments
RACES = ["Chinese", "Malay", "Indian", "Others"]
AGE_BANDS = ["21-29", "30-44", "45-59", "60+"]
INCOME_TIERS = [
    ("<$3K", "low"),
    ("$3K-$8K", "middle"),
    ("$8K-$15K", "upper-middle"),
    (">$15K", "high")
]
HOUSING = ["HDB 1-3 Room", "HDB 4-5 Room", "Condo/EC", "Landed"]

# Occupation archetypes by income tier
OCCUPATIONS = {
    "low": ["hawker stall assistant", "delivery rider", "cleaner", "security guard"],
    "middle": ["admin executive", "nurse", "technician", "sales associate"],
    "upper-middle": ["PME engineer", "teacher", "bank relationship manager", "SME owner"],
    "high": ["senior director", "doctor", "lawyer", "tech lead"]
}

CONCERNS = {
    "Chinese": ["cost of living", "education", "property prices", "CPF"],
    "Malay": ["cost of living", "education subsidies", "employment opportunities", "housing"],
    "Indian": ["employment", "integration", "education", "healthcare"],
    "Others": ["PR/citizenship", "cost of living", "employment", "integration"]
}

FAMILY_STATUS_BY_AGE = {
    "21-29": "single, living with parents",
    "30-44": "married with young children",
    "45-59": "married with teenage/adult children",
    "60+": "retired or semi-retired, grandchildren"
}

def load_grc_profiles() -> dict:
    """Load GRC demographic profiles."""
    path = os.path.join(os.path.dirname(__file__), "..", "data", "grc_profiles.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return get_default_grc_profiles()

def get_default_grc_profiles() -> dict:
    return {
        "Ang Mo Kio GRC": {"pop": 187634, "chinese": 0.76, "malay": 0.12, "indian": 0.09, "others": 0.03, "center": [1.3691, 103.8454]},
        "Tanjong Pagar GRC": {"pop": 148927, "chinese": 0.81, "malay": 0.08, "indian": 0.08, "others": 0.03, "center": [1.2764, 103.8430]},
        "Aljunied GRC": {"pop": 149015, "chinese": 0.62, "malay": 0.15, "indian": 0.18, "others": 0.05, "center": [1.3200, 103.8860]},
        "Marine Parade GRC": {"pop": 146887, "chinese": 0.73, "malay": 0.13, "indian": 0.11, "others": 0.03, "center": [1.3050, 103.9050]},
        "West Coast GRC": {"pop": 145202, "chinese": 0.71, "malay": 0.14, "indian": 0.11, "others": 0.04, "center": [1.3100, 103.7500]},
        "Marsiling-Yew Tee GRC": {"pop": 154032, "chinese": 0.58, "malay": 0.22, "indian": 0.15, "others": 0.05, "center": [1.4300, 103.7700]},
        "Tampines GRC": {"pop": 157543, "chinese": 0.68, "malay": 0.16, "indian": 0.12, "others": 0.04, "center": [1.3530, 103.9440]},
        "Jurong GRC": {"pop": 160231, "chinese": 0.59, "malay": 0.20, "indian": 0.16, "others": 0.05, "center": [1.3400, 103.7000]},
        "Bishan-Toa Payoh GRC": {"pop": 142876, "chinese": 0.78, "malay": 0.10, "indian": 0.09, "others": 0.03, "center": [1.3350, 103.8500]},
        "East Coast GRC": {"pop": 121443, "chinese": 0.74, "malay": 0.11, "indian": 0.12, "others": 0.03, "center": [1.3150, 103.9350]},
        "Sengkang GRC": {"pop": 137980, "chinese": 0.72, "malay": 0.13, "indian": 0.11, "others": 0.04, "center": [1.3920, 103.8950]},
        "Nee Soon GRC": {"pop": 139876, "chinese": 0.64, "malay": 0.18, "indian": 0.14, "others": 0.04, "center": [1.4200, 103.8350]},
    }

def build_personas(target_count: int = 40) -> list[dict]:
    """
    Build representative agent personas weighted to SG demographics.
    Returns ~40 personas, each with a population weight.
    """
    grcs = load_grc_profiles()
    personas = []

    # For each GRC, generate personas proportional to racial mix
    for grc_name, profile in grcs.items():
        for race in RACES:
            race_pct = profile.get(race.lower(), 0.03)
            if race_pct < 0.05:
                continue  # skip tiny segments for this GRC

            # Pick 1-2 age bands per race per GRC
            for age in ["30-44", "60+"]:  # focus on two contrasting ages
                income_label, income_tier = ("$3K-$8K", "middle") if age == "30-44" else ("<$3K", "low")
                housing = "HDB 4-5 Room" if income_tier == "middle" else "HDB 1-3 Room"
                occupation = OCCUPATIONS[income_tier][hash(grc_name + race) % len(OCCUPATIONS[income_tier])]

                weight = profile["pop"] * race_pct * (0.35 if age == "30-44" else 0.25)

                persona = {
                    "age": age,
                    "race": race,
                    "income": income_label,
                    "housing": housing,
                    "grc": grc_name,
                    "occupation": occupation,
                    "family_status": FAMILY_STATUS_BY_AGE[age],
                    "concerns": ", ".join(CONCERNS.get(race, ["cost of living"])[:3]),
                    "weight": round(weight),
                }
                personas.append(persona)

    # Trim to target count if needed
    if len(personas) > target_count:
        personas.sort(key=lambda p: p["weight"], reverse=True)
        personas = personas[:target_count]

    return personas
