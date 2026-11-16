import sys
from pathlib import Path

import pandas as pd

from state_codes import STATE_NAMES

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "eia_residential_price.csv"
OUT = ROOT / "data" / "interim" / "eia_clean.csv"

REQUIRED = ["period", "stateid", "sectorid", "price", "price-units"]
FIRST_YEAR, LAST_YEAR = 2010, 2025


def main():
    if not RAW.exists():
        sys.exit(f"ERROR: missing input {RAW.relative_to(ROOT)} (run scripts/acquire_eia.py first)")
    df = pd.read_csv(RAW, dtype=str)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        sys.exit(f"ERROR: {RAW.name} is missing columns {missing}; found {list(df.columns)}")
    n_raw = len(df)

    df = df[df["sectorid"].str.strip() == "RES"]
    n_res = len(df)

    df["stateid"] = df["stateid"].str.strip().str.upper()
    dropped_geo = sorted(set(df["stateid"]) - set(STATE_NAMES))
    df = df[df["stateid"].isin(STATE_NAMES)]

    df["year"] = pd.to_numeric(df["period"].str.strip().str[:4], errors="coerce").astype("Int64")
    df["price_cents_kwh"] = pd.to_numeric(df["price"].str.replace(",", "").str.strip(), errors="coerce")
    n_null_price = int(df["price_cents_kwh"].isna().sum())
    df = df.dropna(subset=["year", "price_cents_kwh"])
    df = df[df["year"].between(FIRST_YEAR, LAST_YEAR)]

    units = df["price-units"].str.strip().str.lower().unique()
    if len(units) != 1 or "cent" not in units[0]:
        sys.exit(f"ERROR: expected one cents-per-kWh unit, found {list(units)}")

    n_before = len(df)
    df = df.drop_duplicates(subset=["stateid", "year", "price_cents_kwh"])
    n_exact_dupes = n_before - len(df)
    if df.duplicated(subset=["stateid", "year"]).any():
        bad = df[df.duplicated(subset=["stateid", "year"], keep=False)]
        sys.exit(f"ERROR: conflicting prices for the same state-year:\n{bad}")

    out = pd.DataFrame({
        "state": df["stateid"].map(STATE_NAMES),
        "state_abbr": df["stateid"],
        "year": df["year"].astype(int),
        "price_cents_kwh": df["price_cents_kwh"].round(2),
    }).sort_values(["state", "year"])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    print(f"clean_eia: {n_raw} raw rows -> {n_res} residential -> {len(out)} state-years written")
    print(f"  dropped non-state geographies: {dropped_geo}")
    print(f"  rows with missing/non-numeric price dropped: {n_null_price}; exact duplicates removed: {n_exact_dupes}")
    print(f"  states: {out['state'].nunique()}, years: {out['year'].min()}-{out['year'].max()}")


if __name__ == "__main__":
    main()
