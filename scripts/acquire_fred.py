"""Download real median household income for the 50 states from FRED (no API key needed).

One series per state: MEHOINUS<ST>A672N (Census Bureau, annual, constant dollars).
Output: data/raw/fred_median_household_income.csv  (wide: observation_date + one column per series)
"""
import io
import sys
import time
from pathlib import Path

import pandas as pd
import requests

from state_codes import STATE_NAMES

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "raw" / "fred_median_household_income.csv"

URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
START, END = "2010-01-01", "2025-01-01"


def fetch_series(series_id):
    params = {"id": series_id, "cosd": START, "coed": END}
    for attempt in range(3):
        try:
            resp = requests.get(URL, params=params, timeout=60)
        except requests.RequestException as exc:
            if attempt == 2:
                sys.exit(f"ERROR: could not download {series_id} ({type(exc).__name__})")
            time.sleep(2 * (attempt + 1))
            continue
        if resp.status_code == 200:
            df = pd.read_csv(io.StringIO(resp.text), dtype=str)
            if df.shape[1] != 2 or series_id not in df.columns:
                sys.exit(f"ERROR: unexpected response for {series_id}: columns {list(df.columns)}")
            return df.rename(columns={df.columns[0]: "observation_date"})
        if attempt == 2:
            sys.exit(f"ERROR: FRED returned HTTP {resp.status_code} for {series_id}")
        time.sleep(2 * (attempt + 1))


def main():
    series_ids = sorted(f"MEHOINUS{abbr}A672N" for abbr in STATE_NAMES)
    merged = None
    for sid in series_ids:
        df = fetch_series(sid)
        merged = df if merged is None else merged.merge(df, on="observation_date", how="outer")
        time.sleep(0.2)                                   # be polite to the server
    merged = merged.sort_values("observation_date").reset_index(drop=True)
    merged = merged[["observation_date", *series_ids]]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(OUT, index=False, lineterminator="\n")
    print(f"acquire_fred: {len(merged)} dates x {len(series_ids)} series "
          f"({merged['observation_date'].min()} to {merged['observation_date'].max()}) -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
