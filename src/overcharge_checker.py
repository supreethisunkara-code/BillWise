"""
Flags line items that look inflated relative to reference rates, and flags
duplicate diagnostic/consumable charges. This is a heuristic screen meant to
give the patient specific questions to raise with the hospital billing desk --
not a definitive audit.
"""
import json
import os
from collections import Counter

_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "reference_rates.json")
with open(_DATA_PATH) as f:
    RATES = json.load(f)

THRESHOLD = RATES.get("overcharge_threshold_multiplier", 1.5)


def _flat_reference_lookup() -> dict:
    """Flatten the nested reference-rate categories into one description->price map."""
    flat = {}
    for category in ("consultation", "diagnostics", "procedures"):
        for key, price in RATES.get(category, {}).items():
            flat[key.replace("_", " ")] = price
    return flat


REFERENCE_LOOKUP = _flat_reference_lookup()


def _best_match(description: str) -> tuple[str, float] | None:
    """
    Whole-word match between bill description and reference item names.
    Uses word-boundary matching (not raw substring) so short tokens like "ct"
    don't false-match inside unrelated words like "cataract". Picks the
    reference item with the most matching words, requiring at least one
    match on a word of 3+ characters to avoid noise.
    """
    import re
    desc_words = set(re.findall(r"[a-z]+", description.lower()))

    best = None
    best_score = 0
    for ref_name, ref_price in REFERENCE_LOOKUP.items():
        ref_words = ref_name.split()
        significant_ref_words = [w for w in ref_words if len(w) >= 3]
        matches = [w for w in significant_ref_words if w in desc_words]
        if not matches:
            continue
        score = len(matches)
        if score > best_score:
            best_score = score
            best = (ref_name, ref_price)
    return best


def check_overcharges(line_items: list[dict]) -> list[dict]:
    """
    Returns a list of flags, each: {description, amount, reference_price,
    ratio, reason}. Only includes items worth raising with the hospital.
    """
    flags = []

    # 1. Price comparison against reference rates
    for item in line_items:
        desc = item.get("description", "")
        amount = item.get("amount")
        if not desc or amount is None:
            continue
        match = _best_match(desc)
        if match:
            ref_name, ref_price = match
            if ref_price and amount > ref_price * THRESHOLD:
                flags.append({
                    "description": desc,
                    "amount": amount,
                    "reference_price": ref_price,
                    "ratio": round(amount / ref_price, 1),
                    "reason": f"Billed {round(amount / ref_price, 1)}x the typical reference rate "
                              f"for a comparable '{ref_name}' item.",
                })

    # 2. Duplicate diagnostic/procedure charges (same description billed 2+ times same day)
    keyed = Counter()
    for item in line_items:
        key = (item.get("description", "").strip().lower(), item.get("date"))
        if item.get("category") in ("diagnostics", "procedures") and key[0]:
            keyed[key] += 1
    for (desc, date), count in keyed.items():
        if count > 1:
            flags.append({
                "description": desc,
                "amount": None,
                "reference_price": None,
                "ratio": None,
                "reason": f"Billed {count} times" + (f" on {date}" if date else "") +
                          " -- confirm this wasn't a duplicate/billing error.",
            })

    # 3. Consumables flagged as a category worth itemized scrutiny in bulk
    flagged_terms = RATES.get("consumables_flagged_categories", [])
    consumable_total = sum(
        item.get("amount", 0) or 0
        for item in line_items
        if item.get("category") == "consumables"
        or any(term.lower() in item.get("description", "").lower() for term in flagged_terms)
    )
    if consumable_total > 3000:  # arbitrary "worth a second look" threshold
        flags.append({
            "description": "Total consumables (gloves, syringes, PPE, etc.)",
            "amount": consumable_total,
            "reference_price": None,
            "ratio": None,
            "reason": "Consumable charges are a common area of inflation -- ask for an itemized "
                      "breakdown if this seems high for your length of stay.",
        })

    return flags