"""Download + clean + combine BBMP grievance CSVs into one parquet.

Usage:
    python -m src.ingest                 # download all years, write parquet
    python -m src.ingest --years 2024 2025
    python -m src.ingest --local data/raw   # use already-downloaded CSVs

Network note: run this where the internet is open (your laptop / Colab /
Cloud Shell). data.opencity.in must be reachable.
"""
from __future__ import annotations
import argparse
import io
import sys
from pathlib import Path

import pandas as pd
import requests

from . import config as C
from .severity import assign_severity

_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "text/csv,*/*",
}


def _read_source(source: str | Path):
    """Return a file-like/text for pandas. URLs go through requests (custom
    UA) so servers that 403 the default urllib agent still work."""
    s = str(source)
    if s.startswith("http://") or s.startswith("https://"):
        resp = requests.get(s, headers=_HEADERS, timeout=120)
        resp.raise_for_status()
        return io.StringIO(resp.content.decode("utf-8", errors="replace"))
    return source


def load_csv(source: str | Path) -> pd.DataFrame:
    """Read one year's CSV as strings (robust to messy rows)."""
    df = pd.read_csv(
        _read_source(source),
        dtype=str,
        na_values=C.NA_VALUES,
        keep_default_na=True,
        on_bad_lines="warn",
        encoding="utf-8",
    )
    # Some years may have stray columns / different casing — keep known ones.
    df = df.rename(columns=lambda x: x.strip())
    missing = [c for c in C.RAW_COLUMNS if c not in df.columns]
    if missing:
        print(f"  ! warning: missing columns {missing} in {source}", file=sys.stderr)
    keep = [c for c in C.RAW_COLUMNS if c in df.columns]
    return df[keep].rename(columns=C.COLUMN_RENAME)


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize types, whitespace, dates; drop dupes/empties; add time cols."""
    df = df.copy()

    for col in ["category", "sub_category", "ward", "status", "staff_name"]:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()
            df[col] = df[col].str.replace(r"\s+", " ", regex=True)

    # Parse timestamp (source format: 2025-06-19 10:39:00.000000000)
    df["grievance_date"] = pd.to_datetime(
        df["grievance_date"], errors="coerce"
    )

    # Drop rows with no ward or no date (can't be used for the decision).
    before = len(df)
    df = df.dropna(subset=["ward", "grievance_date"])
    df = df[df["ward"].str.len() > 0]

    # Deduplicate on complaint id if present.
    if "complaint_id" in df.columns:
        df = df.drop_duplicates(subset=["complaint_id"])

    # Time helpers.
    df["date"] = df["grievance_date"].dt.date
    df["year"] = df["grievance_date"].dt.year.astype("int16")
    df["month"] = df["grievance_date"].dt.to_period("M").astype(str)

    # Resolution flag.
    df["is_open"] = df["status"].isin(C.OPEN_STATUSES)

    df = assign_severity(df)
    print(f"  cleaned: {before} -> {len(df)} rows")
    return df.reset_index(drop=True)


def build(years=None, local: str | None = None) -> pd.DataFrame:
    years = years or list(C.GRIEVANCE_CSVS.keys())
    frames = []
    for y in years:
        if local:
            path = Path(local) / f"grievances_{y}.csv"
            if not path.exists():
                print(f"  skip {y}: {path} not found", file=sys.stderr)
                continue
            src = path
        else:
            src = C.GRIEVANCE_CSVS[y]
        print(f"[{y}] loading {src}")
        raw = load_csv(src)
        cleaned = clean(raw)
        cleaned["source_year"] = y
        frames.append(cleaned)

    if not frames:
        raise SystemExit("No data loaded. Check --years / --local path / network.")

    combined = pd.concat(frames, ignore_index=True)
    C.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(C.COMBINED_PARQUET, index=False)
    print(f"\nWrote {len(combined):,} rows -> {C.COMBINED_PARQUET}")
    print(combined["category"].value_counts().head(10))
    return combined


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", nargs="*", type=int, default=None)
    ap.add_argument("--local", default=None, help="dir of grievances_<year>.csv")
    args = ap.parse_args()
    build(years=args.years, local=args.local)
