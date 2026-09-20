"""
Rough coverage estimate based on commonly-seen inclusion/exclusion patterns
for standard Indian health insurance policies. This is deliberately
conservative and framed as an ESTIMATE ONLY -- real coverage depends on the
specific policy wording, room-rent capping, co-pay, and sub-limits that this
module has no visibility into.
"""

# Commonly excluded or capped categories across many standard retail health policies.
TYPICALLY_EXCLUDED_KEYWORDS = [
    "admission kit", "registration fee", "attendant charges", "telephone",
    "food charges outside package", "toiletries", "walking aid rental",
]

TYPICALLY_SUBLIMITED_CATEGORIES = {"room_rent"}  # often capped at a % of sum insured or a fixed per-day rate


def estimate_coverage(line_items: list[dict], has_room_rent_capping: bool = True) -> dict:
    """
    Returns a rough split of billed items into likely-covered vs
    likely-excluded/capped, with a clear disclaimer. Does NOT attempt to
    apply co-pay or specific sub-limit math -- flags them for manual review
    instead.
    """
    likely_covered = 0.0
    likely_excluded = 0.0
    needs_review = []

    for item in line_items:
        desc = (item.get("description") or "").lower()
        amount = item.get("amount") or 0
        category = item.get("category")

        if any(kw in desc for kw in TYPICALLY_EXCLUDED_KEYWORDS):
            likely_excluded += amount
        elif category in TYPICALLY_SUBLIMITED_CATEGORIES and has_room_rent_capping:
            needs_review.append(item)
        else:
            likely_covered += amount

    return {
        "likely_covered_estimate": round(likely_covered, 2),
        "likely_excluded_estimate": round(likely_excluded, 2),
        "needs_manual_review": needs_review,
        "disclaimer": (
            "This is a rough estimate based on common policy patterns, not your actual policy "
            "document. Room rent and any sub-limited items need to be checked against your "
            "specific policy's room-rent capping and co-pay clauses. Confirm with your insurer "
            "or TPA before relying on this for a claim decision."
        ),
    }