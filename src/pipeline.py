"""CivicPulse core pipeline (CPU / pandas).

Loads cleaned grievances, then aggregates to a ranked ward x category
priority table — the heart of the officer's "act first" decision.

The SAME functions run on cuDF in benchmark.py (GPU) — they only use
pandas API that cuDF also implements.
"""
from __future__ import annotations
from pathlib import Path

import numpy as np
import pandas as pd

from . import config as C
from .severity import assign_severity, priority_score


# --------------------------------------------------------------------------- #
# Load
# --------------------------------------------------------------------------- #
def load_grievances(years=None) -> pd.DataFrame:
    """Best-effort load. Order: processed parquet -> download -> sample CSV."""
    if C.COMBINED_PARQUET.exists():
        return pd.read_parquet(C.COMBINED_PARQUET)

    # try a live download+clean (works where internet is open)
    try:
        from .ingest import build
        return build(years=years or [2025])
    except Exception as e:  # noqa: BLE001
        print(f"download failed ({e}); falling back to committed sample")

    from .ingest import load_csv, clean
    sample = C.ROOT / "data" / "sample" / "grievances_2025_sample.csv"
    return clean(load_csv(sample))


# --------------------------------------------------------------------------- #
# Amplify (for testing the app + scaling the GPU benchmark)
# --------------------------------------------------------------------------- #
_STATUS_MIX = {"Registered": 0.45, "In Progress": 0.15,
               "Closed": 0.33, "ReOpen": 0.07}


def amplify(df: pd.DataFrame, target_rows: int, seed: int = 7) -> pd.DataFrame:
    """Bootstrap real (category, sub_category, ward, staff_name) tuples up to
    `target_rows`, spread across a realistic date range with a realistic
    status mix. Used to (a) demo the app on believable volume and (b) create a
    large frame for the CPU-vs-GPU benchmark. Clearly synthetic amplification.
    """
    rng = np.random.default_rng(seed)
    base = df[["category", "sub_category", "ward", "staff_name"]].dropna(subset=["ward"])
    idx = rng.integers(0, len(base), size=target_rows)
    out = base.iloc[idx].reset_index(drop=True)

    # dates spread over ~3 years ending today
    end = pd.Timestamp.today().normalize()
    start = end - pd.Timedelta(days=3 * 365)
    span = (end - start).days
    offsets = rng.integers(0, span, size=target_rows)
    out["grievance_date"] = start + pd.to_timedelta(offsets, unit="D")

    statuses = list(_STATUS_MIX.keys())
    probs = list(_STATUS_MIX.values())
    out["status"] = rng.choice(statuses, size=target_rows, p=probs)
    out["complaint_id"] = np.arange(target_rows)

    out["date"] = out["grievance_date"].dt.date
    out["year"] = out["grievance_date"].dt.year.astype("int16")
    out["month"] = out["grievance_date"].dt.to_period("M").astype(str)
    out["is_open"] = out["status"].isin(C.OPEN_STATUSES)
    out = assign_severity(out)
    return out


# --------------------------------------------------------------------------- #
# Aggregate + rank  (this is the compute that GPU accelerates)
# --------------------------------------------------------------------------- #
def rank_hotspots(df: pd.DataFrame,
                  categories=None,
                  min_severity: int = 1,
                  since=None,
                  until=None) -> pd.DataFrame:
    """Filter, then group by ward x category and compute a priority score.
    Returns a ranked table (highest priority first)."""
    d = df
    if since is not None:
        d = d[d["grievance_date"] >= pd.Timestamp(since)]
    if until is not None:
        d = d[d["grievance_date"] <= pd.Timestamp(until)]
    if categories:
        d = d[d["category"].isin(categories)]
    if min_severity > 1:
        d = d[d["severity"] >= min_severity]

    if len(d) == 0:
        return pd.DataFrame(columns=["ward", "category", "complaints",
                                     "unresolved_rate", "severity",
                                     "last_seen", "priority"])

    ref = pd.Timestamp(d["grievance_date"].max())
    g = (d.groupby(["ward", "category"], observed=True)
           .agg(complaints=("complaint_id", "count"),
                unresolved_rate=("is_open", "mean"),
                severity=("severity", "max"),
                last_date=("grievance_date", "max"))
           .reset_index())

    g["recency_days"] = (ref - g["last_date"]).dt.days.clip(lower=0)
    g["priority"] = priority_score(
        g["complaints"].to_numpy(),
        g["severity"].to_numpy(),
        g["unresolved_rate"].to_numpy(),
        g["recency_days"].to_numpy(),
    )
    g["last_seen"] = pd.to_datetime(g["last_date"]).dt.date
    g = g.sort_values("priority", ascending=False).reset_index(drop=True)
    g["rank"] = g.index + 1
    return g[["rank", "ward", "category", "complaints", "unresolved_rate",
              "severity", "last_seen", "priority"]]


def ward_rollup(hotspots: pd.DataFrame) -> pd.DataFrame:
    """Roll hotspots up to a per-ward priority (for map / ward ranking)."""
    if len(hotspots) == 0:
        return hotspots
    r = (hotspots.groupby("ward")
         .agg(total_complaints=("complaints", "sum"),
              top_priority=("priority", "max"),
              total_priority=("priority", "sum"),
              worst_severity=("severity", "max"))
         .reset_index()
         .sort_values("total_priority", ascending=False)
         .reset_index(drop=True))
    return r


def kpis(df: pd.DataFrame) -> dict:
    return {
        "total_complaints": int(len(df)),
        "unresolved_pct": round(100 * float(df["is_open"].mean()), 1) if len(df) else 0.0,
        "wards": int(df["ward"].nunique()),
        "public_safety_pct": round(100 * float(df["is_public_safety"].mean()), 1) if len(df) else 0.0,
        "date_min": str(df["grievance_date"].min().date()) if len(df) else "-",
        "date_max": str(df["grievance_date"].max().date()) if len(df) else "-",
    }


if __name__ == "__main__":
    base = load_grievances()
    print("loaded", len(base), "rows")
    big = amplify(base, 40_000)
    print("amplified to", len(big))
    hs = rank_hotspots(big, min_severity=1)
    print("\nTop 10 hotspots:")
    print(hs.head(10).to_string(index=False))
    print("\nKPIs:", kpis(big))
