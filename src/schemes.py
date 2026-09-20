"""
Heuristic eligibility screening against a small set of major government
health schemes. This intentionally does NOT claim definitive eligibility --
PM-JAY in particular depends on SECC 2011 database inclusion, which cannot be
determined from income alone. Always route the user to the official
check_url/helpline for a real determination.
"""
import json
import os

_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "scheme_rules.json")
with open(_DATA_PATH) as f:
    SCHEME_DATA = json.load(f)["schemes"]


def check_eligibility(annual_income: float, state: str, employment_type: str, category: str | None = None) -> list[dict]:
    """
    Returns a list of {scheme_name, likely_eligible, note, check_url, helpline}
    for each scheme worth the user's attention. 'likely_eligible' is always a
    heuristic, never a guarantee.
    """
    results = []
    for scheme in SCHEME_DATA:
        heuristic = scheme.get("heuristic_eligibility", {})
        likely = None
        note = heuristic.get("note", "")

        if scheme["id"] == "pmjay":
            max_income = heuristic.get("max_annual_income")
            likely = annual_income is not None and annual_income <= max_income
            note = (
                "Income suggests you may fall in the target group, but PM-JAY eligibility is "
                "actually based on SECC 2011 deprivation criteria, not income alone. Check your "
                "name on the official portal to be sure."
                if likely else
                "Income is above PM-JAY's usual target range, but check anyway -- some states "
                "extend coverage further, and SECC-listed households qualify regardless of current income."
            )
        elif scheme["id"] == "cghs":
            allowed_types = heuristic.get("employment_type", [])
            likely = employment_type in allowed_types
            note = "CGHS applies to central government employees/pensioners and their dependents."
        elif scheme["id"] == "state_generic":
            likely = None  # can't heuristically evaluate without a per-state rules table
            note = f"{state or 'Your state'} likely runs its own scheme -- worth checking separately."

        results.append({
            "scheme_name": scheme["name"],
            "likely_eligible": likely,
            "note": note,
            "check_url": scheme.get("check_url"),
            "helpline": scheme.get("helpline"),
        })

    return results