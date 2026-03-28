"""
Load real Singapore government Census + Election data from CSVs.
Enhances demographics with actual population distributions.
"""
import csv
import os
import json
from collections import defaultdict

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def _read_csv(filename: str) -> list[dict]:
    """Read a CSV file from the data directory."""
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_pop_age_sex() -> dict:
    """
    Load Census 2020 population by planning area, age group, and sex.
    Returns: {planning_area: {age_band: population}}
    """
    rows = _read_csv("pop_age_sex.csv")
    result = {}
    for row in rows:
        name = row.get("Number", "").strip()
        if not name or name == "Total" or " - " in name:
            # Skip subzones, keep only planning area totals
            if " - Total" in name:
                area = name.replace(" - Total", "").strip()
            else:
                continue
        else:
            area = name

        def _safe_int(v):
            try:
                return int(v.replace(",", "").strip())
            except (ValueError, AttributeError):
                return 0

        result[area] = {
            "total": _safe_int(row.get("Total_Total", "0")),
            "0-19": sum(_safe_int(row.get(f"Total_{a}", "0")) for a in ["0_4", "5_9", "10_14", "15_19"]),
            "20-29": sum(_safe_int(row.get(f"Total_{a}", "0")) for a in ["20_24", "25_29"]),
            "30-44": sum(_safe_int(row.get(f"Total_{a}", "0")) for a in ["30_34", "35_39", "40_44"]),
            "45-59": sum(_safe_int(row.get(f"Total_{a}", "0")) for a in ["45_49", "50_54", "55_59"]),
            "60+": sum(_safe_int(row.get(f"Total_{a}", "0")) for a in
                       ["60_64", "65_69", "70_74", "75_79", "80_84", "85_89", "90andOver"]),
        }
    return result


def load_pop_ethnicity() -> dict:
    """
    Load Census 2020 population by planning area and ethnic group.
    Returns: {planning_area: {chinese: N, malay: N, indian: N, others: N, total: N}}
    """
    rows = _read_csv("pop_ethnicity.csv")
    result = {}
    for row in rows:
        name = row.get("Number", "").strip()
        if not name or name == "Total" or " - " in name:
            if " - Total" in name:
                area = name.replace(" - Total", "").strip()
            else:
                continue
        else:
            area = name

        def _safe_int(v):
            try:
                return int(v.replace(",", "").strip())
            except (ValueError, AttributeError):
                return 0

        total = _safe_int(row.get("Total_Total", "0"))
        result[area] = {
            "total": total,
            "chinese": _safe_int(row.get("Chinese_Total", "0")),
            "malays": _safe_int(row.get("Malays_Total", "0")),
            "indians": _safe_int(row.get("Indians_Total", "0")),
            "others": _safe_int(row.get("Others_Total", "0")),
        }
    return result


def load_households_dwelling() -> dict:
    """
    Load Census 2020 households by dwelling type and planning area.
    Returns: {planning_area: {hdb_1_3: N, hdb_4_5: N, condo: N, landed: N, total: N}}
    """
    rows = _read_csv("households_dwelling.csv")
    result = {}
    for row in rows:
        name = row.get("Number", "").strip()
        if not name or name == "Total":
            continue

        def _safe_int(v):
            try:
                return int(v.replace(",", "").strip())
            except (ValueError, AttributeError):
                return 0

        result[name] = {
            "total": _safe_int(row.get("Total", "0")),
            "hdb_1_3": _safe_int(row.get("HDBDwellings_1_and2_RoomFlats1", "0")) +
                       _safe_int(row.get("HDBDwellings_3_RoomFlats", "0")),
            "hdb_4_5": _safe_int(row.get("HDBDwellings_4_RoomFlats", "0")) +
                       _safe_int(row.get("HDBDwellings_5_RoomandExecutiveFlats", "0")),
            "condo": _safe_int(row.get("CondominiumsandOtherApartments", "0")),
            "landed": _safe_int(row.get("LandedProperties", "0")),
        }
    return result


def load_income_distribution() -> dict:
    """
    Load Census 2020 household income distribution by planning area.
    Returns: {planning_area: {median_approx: float, low_pct: float, mid_pct: float, high_pct: float}}
    """
    rows = _read_csv("income_by_area.csv")
    result = {}
    for row in rows:
        name = row.get("Number", "").strip()
        if not name or name == "Total":
            continue

        def _safe_int(v):
            try:
                return int(v.replace(",", "").strip())
            except (ValueError, AttributeError):
                return 0

        total = _safe_int(row.get("Total", "0"))
        no_emp = _safe_int(row.get("NoEmployedPerson", "0"))
        employed = total - no_emp if total > no_emp else total

        # Low income: <$3K
        low = sum(_safe_int(row.get(c, "0")) for c in ["Below_1_000", "1_000_1_999", "2_000_2_999"])
        # Mid income: $3K-$10K
        mid = sum(_safe_int(row.get(c, "0")) for c in
                  ["3_000_3_999", "4_000_4_999", "5_000_5_999", "6_000_6_999",
                   "7_000_7_999", "8_000_8_999", "9_000_9_999"])
        # High income: $10K+
        high = sum(_safe_int(row.get(c, "0")) for c in
                   ["10_000_10_999", "11_000_11_999", "12_000_12_999", "13_000_13_999",
                    "14_000_14_999", "15_000_17_499", "17_500_19_999", "20_000andOver"])

        emp_total = low + mid + high or 1
        result[name] = {
            "total_households": total,
            "low_pct": round(low / emp_total, 3),
            "mid_pct": round(mid / emp_total, 3),
            "high_pct": round(high / emp_total, 3),
            # Approximate median by finding which band contains the 50th percentile
            "median_approx": _approx_median(row),
        }
    return result


def _approx_median(row: dict) -> float:
    """Approximate median household income from band distribution."""
    bands = [
        ("Below_1_000", 500),
        ("1_000_1_999", 1500),
        ("2_000_2_999", 2500),
        ("3_000_3_999", 3500),
        ("4_000_4_999", 4500),
        ("5_000_5_999", 5500),
        ("6_000_6_999", 6500),
        ("7_000_7_999", 7500),
        ("8_000_8_999", 8500),
        ("9_000_9_999", 9500),
        ("10_000_10_999", 10500),
        ("11_000_11_999", 11500),
        ("12_000_12_999", 12500),
        ("13_000_13_999", 13500),
        ("14_000_14_999", 14500),
        ("15_000_17_499", 16250),
        ("17_500_19_999", 18750),
        ("20_000andOver", 25000),
    ]

    def _safe_int(v):
        try:
            return int(v.replace(",", "").strip())
        except (ValueError, AttributeError):
            return 0

    counts = [(_safe_int(row.get(col, "0")), mid) for col, mid in bands]
    total = sum(c for c, _ in counts)
    if total == 0:
        return 0

    cumulative = 0
    for count, midpoint in counts:
        cumulative += count
        if cumulative >= total / 2:
            return midpoint
    return 25000


def load_ge_results(year: int = 2020) -> dict:
    """
    Load general election results for a given year.
    Returns: {constituency: [{party, candidates, vote_count, vote_percentage}]}
    """
    rows = _read_csv("ge_results.csv")
    result = defaultdict(list)
    for row in rows:
        if str(row.get("year", "")).strip() != str(year):
            continue
        constituency = row.get("constituency", "").strip()
        result[constituency].append({
            "party": row.get("party", "").strip(),
            "candidates": row.get("candidates", "").strip(),
            "vote_count": int(row.get("vote_count", "0").strip()),
            "vote_percentage": float(row.get("vote_percentage", "0").strip()),
            "constituency_type": row.get("constituency_type", "").strip(),
        })
    return dict(result)


def load_voter_turnout(year: int = 2020) -> dict:
    """
    Load voter turnout data for a given year.
    Returns: {constituency: {registered_electors, rejected_votes, spoilt_ballots}}
    """
    rows = _read_csv("voter_turnout.csv")
    result = {}
    for row in rows:
        if str(row.get("year", "")).strip() != str(year):
            continue
        constituency = row.get("constituency", "").strip()
        result[constituency] = {
            "registered_electors": int(row.get("no_of_registered_electors", "0").strip()),
            "rejected_votes": int(row.get("no_of_rejected_votes", "0").strip()),
            "spoilt_ballots": int(row.get("no_of_spoilt_ballot_papers", "0").strip()),
        }
    return result


def get_enriched_grc_profiles() -> dict:
    """
    Build enriched GRC profiles by combining all real data sources.
    Falls back to grc_profiles.json for GRC-specific data (since Census data
    is at planning-area level, not constituency level).
    """
    # Load base profiles
    base_path = os.path.join(DATA_DIR, "grc_profiles.json")
    with open(base_path) as f:
        base = json.load(f)

    # Load real data
    ethnicity = load_pop_ethnicity()
    income = load_income_distribution()
    ge_results = load_ge_results(2020)
    turnout = load_voter_turnout(2020)

    # Enrich each GRC
    for grc_name, profile in base.items():
        # Strip "GRC" / "SMC" suffix for matching
        short_name = grc_name.replace(" GRC", "").replace(" SMC", "").strip()

        # Add GE2020 results if available
        ge_key = next((k for k in ge_results if short_name.upper() in k.upper()), None)
        if ge_key:
            parties = ge_results[ge_key]
            profile["ge2020"] = {
                "results": parties,
                "winner": max(parties, key=lambda p: p["vote_percentage"])["party"],
                "margin": abs(parties[0]["vote_percentage"] - parties[-1]["vote_percentage"])
                          if len(parties) > 1 else 1.0,
            }

        # Add turnout data
        turnout_key = next((k for k in turnout if short_name.upper() in k.upper()), None)
        if turnout_key:
            profile["turnout"] = turnout[turnout_key]

    return base


# Quick test
if __name__ == "__main__":
    print("=== Population Age/Sex ===")
    age = load_pop_age_sex()
    print(f"  {len(age)} planning areas")
    if "Ang Mo Kio" in age:
        print(f"  Ang Mo Kio: {age['Ang Mo Kio']}")

    print("\n=== Ethnicity ===")
    eth = load_pop_ethnicity()
    print(f"  {len(eth)} planning areas")
    if "Ang Mo Kio" in eth:
        print(f"  Ang Mo Kio: {eth['Ang Mo Kio']}")

    print("\n=== Households ===")
    hh = load_households_dwelling()
    print(f"  {len(hh)} planning areas")

    print("\n=== Income ===")
    inc = load_income_distribution()
    print(f"  {len(inc)} planning areas")
    if "Ang Mo Kio" in inc:
        print(f"  Ang Mo Kio: {inc['Ang Mo Kio']}")

    print("\n=== GE2020 Results ===")
    ge = load_ge_results(2020)
    print(f"  {len(ge)} constituencies")
    for k, v in list(ge.items())[:3]:
        print(f"  {k}: {v[0]['party']} {v[0]['vote_percentage']:.1%}")

    print("\n=== Enriched GRC Profiles ===")
    profiles = get_enriched_grc_profiles()
    for name, p in list(profiles.items())[:2]:
        ge = p.get("ge2020", {})
        print(f"  {name}: winner={ge.get('winner','?')}, margin={ge.get('margin',0):.2%}")
