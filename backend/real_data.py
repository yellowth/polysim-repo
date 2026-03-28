"""
Load real Singapore government Census + Election data from CSVs.
Supports GE2020 and GE2025 results with robust constituency matching.
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


def _safe_int(v) -> int:
    try:
        return int(str(v).replace(",", "").strip())
    except (ValueError, AttributeError, TypeError):
        return 0


def _safe_float(v) -> float:
    try:
        return float(str(v).replace(",", "").strip())
    except (ValueError, AttributeError, TypeError):
        return 0.0


def load_pop_age_sex() -> dict:
    """Load Census 2020 population by planning area, age group, and sex."""
    rows = _read_csv("pop_age_sex.csv")
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
    """Load Census 2020 population by planning area and ethnic group."""
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

        result[area] = {
            "total": _safe_int(row.get("Total_Total", "0")),
            "chinese": _safe_int(row.get("Chinese_Total", "0")),
            "malays": _safe_int(row.get("Malays_Total", "0")),
            "indians": _safe_int(row.get("Indians_Total", "0")),
            "others": _safe_int(row.get("Others_Total", "0")),
        }
    return result


def load_households_dwelling() -> dict:
    """Load Census 2020 households by dwelling type and planning area."""
    rows = _read_csv("households_dwelling.csv")
    result = {}
    for row in rows:
        name = row.get("Number", "").strip()
        if not name or name == "Total":
            continue

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
    """Load Census 2020 household income distribution by planning area."""
    rows = _read_csv("income_by_area.csv")
    result = {}
    for row in rows:
        name = row.get("Number", "").strip()
        if not name or name == "Total":
            continue

        total = _safe_int(row.get("Total", "0"))
        no_emp = _safe_int(row.get("NoEmployedPerson", "0"))

        low = sum(_safe_int(row.get(c, "0")) for c in ["Below_1_000", "1_000_1_999", "2_000_2_999"])
        mid = sum(_safe_int(row.get(c, "0")) for c in
                  ["3_000_3_999", "4_000_4_999", "5_000_5_999", "6_000_6_999",
                   "7_000_7_999", "8_000_8_999", "9_000_9_999"])
        high = sum(_safe_int(row.get(c, "0")) for c in
                   ["10_000_10_999", "11_000_11_999", "12_000_12_999", "13_000_13_999",
                    "14_000_14_999", "15_000_17_499", "17_500_19_999", "20_000andOver"])

        emp_total = low + mid + high or 1
        result[name] = {
            "total_households": total,
            "low_pct": round(low / emp_total, 3),
            "mid_pct": round(mid / emp_total, 3),
            "high_pct": round(high / emp_total, 3),
            "median_approx": _approx_median(row),
        }
    return result


def _approx_median(row: dict) -> float:
    """Approximate median household income from band distribution."""
    bands = [
        ("Below_1_000", 500), ("1_000_1_999", 1500), ("2_000_2_999", 2500),
        ("3_000_3_999", 3500), ("4_000_4_999", 4500), ("5_000_5_999", 5500),
        ("6_000_6_999", 6500), ("7_000_7_999", 7500), ("8_000_8_999", 8500),
        ("9_000_9_999", 9500), ("10_000_10_999", 10500), ("11_000_11_999", 11500),
        ("12_000_12_999", 12500), ("13_000_13_999", 13500), ("14_000_14_999", 14500),
        ("15_000_17_499", 16250), ("17_500_19_999", 18750), ("20_000andOver", 25000),
    ]
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


def _normalize_constituency(name: str) -> str:
    """Normalize constituency name for robust matching."""
    return name.upper().replace(" GRC", "").replace(" SMC", "").replace("-", " ").strip()


def _match_constituency(short_name: str, candidates: dict) -> str | None:
    """
    Match a GRC name to a key in candidates dict using normalized comparison.
    Uses exact match first, then falls back to best substring match.
    """
    norm = _normalize_constituency(short_name)

    # Pass 1: exact normalized match
    for k in candidates:
        if _normalize_constituency(k) == norm:
            return k

    # Pass 2: one contains the other (handles "Jurong" matching "Jurong Central")
    best_match = None
    best_score = 0
    for k in candidates:
        k_norm = _normalize_constituency(k)
        if norm in k_norm or k_norm in norm:
            # Prefer the closest length match
            score = min(len(norm), len(k_norm)) / max(len(norm), len(k_norm))
            if score > best_score:
                best_score = score
                best_match = k

    return best_match if best_score > 0.5 else None


def load_ge_results(year: int = 2020) -> dict:
    """
    Load general election results for a given year.
    Parties are sorted by vote_percentage descending (winner first).
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
            "vote_count": _safe_int(row.get("vote_count", "0")),
            "vote_percentage": _safe_float(row.get("vote_percentage", "0")),
            "constituency_type": row.get("constituency_type", "").strip(),
        })

    # Sort each constituency's parties by vote share (winner first)
    for constituency in result:
        result[constituency].sort(key=lambda p: p["vote_percentage"], reverse=True)

    return dict(result)


def load_voter_turnout(year: int = 2020) -> dict:
    """Load voter turnout data for a given year."""
    rows = _read_csv("voter_turnout.csv")
    result = {}
    for row in rows:
        if str(row.get("year", "")).strip() != str(year):
            continue
        constituency = row.get("constituency", "").strip()
        result[constituency] = {
            "registered_electors": _safe_int(row.get("no_of_registered_electors", "0")),
            "rejected_votes": _safe_int(row.get("no_of_rejected_votes", "0")),
            "spoilt_ballots": _safe_int(row.get("no_of_spoilt_ballot_papers", "0")),
        }
    return result


def get_enriched_grc_profiles(ge_year: int = 2025) -> dict:
    """
    Build enriched GRC profiles by combining all real data sources.
    Supports both GE2020 and GE2025 results.
    """
    base_path = os.path.join(DATA_DIR, "grc_profiles.json")
    if not os.path.exists(base_path):
        return {}
    with open(base_path) as f:
        base = json.load(f)

    ge_results = load_ge_results(ge_year)
    turnout = load_voter_turnout(ge_year)

    for grc_name, profile in base.items():
        # Match using robust constituency matcher
        ge_key = _match_constituency(grc_name, ge_results)
        if ge_key:
            parties = ge_results[ge_key]
            # Parties already sorted by vote_percentage desc
            winner = parties[0]["party"] if parties else "Unknown"
            margin = (parties[0]["vote_percentage"] - parties[1]["vote_percentage"]) \
                if len(parties) > 1 else 1.0

            profile[f"ge{ge_year}"] = {
                "results": parties,
                "winner": winner,
                "margin": abs(margin),
            }

        turnout_key = _match_constituency(grc_name, turnout)
        if turnout_key:
            profile["turnout"] = turnout[turnout_key]

    return base


if __name__ == "__main__":
    print("=== GE2025 Results ===")
    ge25 = load_ge_results(2025)
    print(f"  {len(ge25)} constituencies")
    for k, v in list(ge25.items())[:5]:
        print(f"  {k}: {v[0]['party']} {v[0]['vote_percentage']:.1%} (winner)")

    print("\n=== Enriched GRC Profiles (GE2025) ===")
    profiles = get_enriched_grc_profiles(2025)
    for name, p in list(profiles.items())[:5]:
        ge = p.get("ge2025", {})
        print(f"  {name}: winner={ge.get('winner','?')}, margin={ge.get('margin',0):.2%}")
