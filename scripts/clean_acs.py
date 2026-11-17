import sys
from pathlib import Path

import numpy as np
import pandas as pd

from state_codes import STATE_ABBRS

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "acs_b25040.csv"
OUT = ROOT / "data" / "interim" / "acs_clean.csv"

COLS = {
    "B25040_001E": "total_units",
    "B25040_001M": "total_units_moe",
    "B25040_004E": "units_electric_heat",
    "B25040_004M": "units_electric_heat_moe",
}
REQUIRED = ["NAME", "year", "estimate_type", *COLS]


def proportion_moe(p, moe_num, moe_den, den):
    """Census ACS formula for the MOE of a proportion (numerator is a subset of denominator)."""
    radicand = moe_num**2 - (p**2) * (moe_den**2)
    radicand = np.where(radicand < 0, moe_num**2 + (p**2) * (moe_den**2), radicand)
    return np.sqrt(radicand) / den


def main():
    if not RAW.exists():
        sys.exit(f"ERROR: missing input {RAW.relative_to(ROOT)} (run scripts/acquire_acs.py first)")
    df = pd.read_csv(RAW, dtype=str)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        sys.exit(f"ERROR: {RAW.name} is missing columns {missing}")
    n_raw = len(df)

    df["NAME"] = df["NAME"].str.strip()
    dropped_geo = sorted(set(df["NAME"]) - set(STATE_ABBRS))
    df = df[df["NAME"].isin(STATE_ABBRS)].copy()

    n_sentinel = 0
    for raw_col, new_col in COLS.items():
        vals = pd.to_numeric(df[raw_col], errors="coerce")
        sentinel = vals < 0
        n_sentinel += int(sentinel.sum())
        df[new_col] = vals.mask(sentinel)

    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df["estimate_type"] = df["estimate_type"].str.strip().str.lower()

    n_before = len(df)
    df = df.dropna(subset=["year", "total_units", "units_electric_heat"])
    n_dropped_missing = n_before - len(df)

    bad = df[df["units_electric_heat"] > df["total_units"]]
    if not bad.empty:
        sys.exit(f"ERROR: electric-heat units exceed total units:\n{bad[['NAME', 'year']]}")
    if df.duplicated(subset=["NAME", "year"]).any():
        sys.exit("ERROR: duplicate state-year rows in ACS data")

    df["share_electric_heat"] = df["units_electric_heat"] / df["total_units"]
    df["share_electric_heat_moe"] = proportion_moe(
        df["share_electric_heat"], df["units_electric_heat_moe"], df["total_units_moe"], df["total_units"]
    )

    out = pd.DataFrame({
        "state": df["NAME"],
        "year": df["year"].astype(int),
        "total_units": df["total_units"].astype(int),
        "total_units_moe": df["total_units_moe"].astype("Int64"),
        "units_electric_heat": df["units_electric_heat"].astype(int),
        "units_electric_heat_moe": df["units_electric_heat_moe"].astype("Int64"),
        "share_electric_heat": df["share_electric_heat"].round(6),
        "share_electric_heat_moe": df["share_electric_heat_moe"].round(6),
        "estimate_type": df["estimate_type"],
    }).sort_values(["state", "year"])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    print(f"clean_acs: {n_raw} raw rows -> {len(out)} state-years written")
    print(f"  dropped non-state geographies: {dropped_geo}")
    print(f"  Census sentinel values set to missing: {n_sentinel}; rows dropped for missing counts: {n_dropped_missing}")
    print(f"  estimate types by year: { {t: [int(y) for y in sorted(g)] for t, g in out.groupby('estimate_type')['year'].unique().items()}}")


if __name__ == "__main__":
    main()
