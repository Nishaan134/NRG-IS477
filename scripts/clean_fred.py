import re
import sys
from pathlib import Path

import pandas as pd

from state_codes import STATE_NAMES

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "fred_median_household_income.csv"
OUT = ROOT / "data" / "interim" / "fred_clean.csv"

SERIES_RE = re.compile(r"^MEHOINUS([A-Z]{2})A672N$")


def main():
    if not RAW.exists():
        sys.exit(f"ERROR: missing input {RAW.relative_to(ROOT)} (run scripts/acquire_fred.py first)")
    wide = pd.read_csv(RAW, dtype=str)
    date_col = wide.columns[0]
    if date_col.lower() not in ("observation_date", "date"):
        sys.exit(f"ERROR: expected first column observation_date, found {date_col!r}")

    col_to_abbr = {}
    for col in wide.columns[1:]:
        m = SERIES_RE.match(col.strip())
        if not m or m.group(1) not in STATE_NAMES:
            sys.exit(f"ERROR: unrecognized FRED series column {col!r}")
        col_to_abbr[col] = m.group(1)
    missing_states = sorted(set(STATE_NAMES) - set(col_to_abbr.values()))
    if missing_states:
        print(f"  WARNING: no FRED series for {missing_states}")

    long = wide.melt(id_vars=date_col, var_name="series_id", value_name="value")
    long["state_abbr"] = long["series_id"].map(col_to_abbr)
    long["year"] = pd.to_datetime(long[date_col], errors="coerce").dt.year
    long["real_median_income"] = pd.to_numeric(long["value"].str.strip(), errors="coerce")
    n_missing = int(long["real_median_income"].isna().sum())
    long = long.dropna(subset=["year", "real_median_income"])

    if long.duplicated(subset=["state_abbr", "year"]).any():
        sys.exit("ERROR: duplicate state-year rows in FRED data")

    out = pd.DataFrame({
        "state": long["state_abbr"].map(STATE_NAMES),
        "state_abbr": long["state_abbr"],
        "year": long["year"].astype(int),
        "real_median_income": long["real_median_income"].round(0).astype(int),
    }).sort_values(["state", "year"])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    print(f"clean_fred: {len(wide)} dates x {len(col_to_abbr)} series -> {len(out)} state-years written")
    print(f"  missing ('.') values dropped: {n_missing}")
    print(f"  states: {out['state'].nunique()}, years: {out['year'].min()}-{out['year'].max()}")


if __name__ == "__main__":
    main()
