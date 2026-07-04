"""Severity assignment and priority scoring.

The officer's decision is: *given a fixed weekly budget/crew, which
ward x issue-type should I act on first?* Priority must therefore combine
how bad an issue is (severity), how much of it there is (volume), how stuck
it is (unresolved backlog), and how fresh it is (recency).

Severity is a defensible rules map; Gemini later refines the narrative, not
the number, so the ranking stays transparent and explainable to judges.
"""
from __future__ import annotations
import numpy as np

# Base severity by Category (1 = admin/low, 5 = public-health/safety critical).
CATEGORY_SEVERITY = {
    "Health Dept": 5,
    "veterinary": 4,
    "Storm  Water Drain(SWD)": 4,
    "Storm Water Drain(SWD)": 4,
    "Sanitation": 4,
    "Road Maintenance(Engg)": 3,
    "Road Infrastructure": 3,
    "Solid Waste (Garbage) Related": 3,
    "Electrical": 3,
    "Forest": 3,
    "Parks and Play grounds": 2,
    "Town Planning": 2,
    "Plastic": 2,
    "Advertisement": 1,
    "Traffic Engineer Cell (TEC)": 3,
    "E khata / Khata services": 1,
    "Revenue Department": 1,
    "Information Technology": 1,
    "Others": 1,
}
DEFAULT_SEVERITY = 2

# Sub-category keywords that bump severity regardless of category
# (life-safety / public-health signals buried inside a mid category).
SUBCATEGORY_HIGH = [
    "dengue", "mosquito", "fatally injured", "rabid", "dog bite",
    "open defecation", "public toilet", "sewerage", "water stagnation",
    "water leakage", "pothole", "dead animal", "burning of garbage",
]


def _clean_cat(c: str) -> str:
    return " ".join(str(c).split())  # collapse double spaces


def assign_severity(df):
    """Add `severity` (1-5) and `is_public_safety` columns. Works on
    pandas OR cudf frames (only uses shared API)."""
    cat = df["category"].fillna("Others").map(_clean_cat)
    sev = cat.map(CATEGORY_SEVERITY).fillna(DEFAULT_SEVERITY)

    sub = df["sub_category"].fillna("").str.lower()
    bump = sub.apply(lambda s: any(k in s for k in SUBCATEGORY_HIGH)) \
        if hasattr(sub, "apply") else sub.str.contains("|".join(SUBCATEGORY_HIGH))
    # Where a high-signal sub-category is present, floor severity at 4.
    sev = sev.where(~bump, other=np.maximum(sev, 4))

    df = df.copy()
    df["severity"] = sev.astype("int8")
    df["is_public_safety"] = (df["severity"] >= 4)
    return df


def priority_score(count, severity, unresolved_rate, recency_days):
    """Vectorizable priority score for a ward x category group.

    - volume via log so a few nasty issues aren't buried by garbage-dump spam
    - severity dominates (squared)
    - unresolved backlog inflates priority (stuck work needs attention)
    - recency decays over ~30 days
    """
    volume = np.log1p(count)
    backlog = 0.5 + unresolved_rate            # 0.5 .. 1.5
    recency = np.exp(-recency_days / 30.0)     # 1.0 (today) .. ~0 (old)
    return (severity ** 2) * volume * backlog * (0.5 + 0.5 * recency)
