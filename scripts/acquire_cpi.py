"""Download the price index used to deflate electricity prices, as annual averages.

FRED's income series (MEHOINUS<ST>A672N) is in constant dollars deflated with the chained CPI-U
(C-CPI-U) for 2000 onward (FRED series notes), so the matching index is BLS series SUUR0000SA0
(Chained CPI for All Urban Consumers, all items; monthly, Dec 1999 = 100).

The monthly series is downloaded and averaged here (not by FRED) so the number of months behind
each annual value is explicit. Months with no value (".") are skipped. 2010-2024 must have all
12 months; 2025 may have fewer if a month was never published, and the script says so.

Output: data/raw/cpi.csv   (observation_date, SUUR0000SA0, months_used)
"""
import io
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "raw" / "cpi.csv"

SERIES = "SUUR0000SA0"
URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
FIRST_YEAR, LAST_YEAR = 2010, 2025
MIN_MONTHS_LAST_YEAR = 11


def main():
    params = {"id": SERIES, "cosd": f"{FIRST_YEAR}-01-01", "coed": f"{LAST_YEAR}-12-01"}
    resp = None
    for attempt in range(3):
        try:
            resp = requests.get(URL, params=params, timeout=60)
            if resp.status_code == 200:
                break
        except requests.RequestException:
            pass
        if attempt == 2:
            sys.exit(f"ERROR: could not download {SERIES} from FRED")
        time.sleep(2 * (attempt + 1))

    df = pd.read_csv(io.StringIO(resp.text), dtype=str)
    if df.shape[1] != 2 or SERIES not in df.columns:
        sys.exit(f"ERROR: unexpected response columns {list(df.columns)}")
    df = df.rename(columns={df.columns[0]: "observation_date"})
    df["date"] = pd.to_datetime(df["observation_date"], errors="coerce")
    df["value"] = pd.to_numeric(df[SERIES].str.strip(), errors="coerce")   # "." -> NaN
    if df["date"].isna().any():
        sys.exit("ERROR: unparseable dates in the FRED response")
    df["year"] = df["date"].dt.year

    g = df.groupby("year")
    annual = pd.DataFrame({SERIES: g["value"].mean().round(3), "months_used": g["value"].count()})
    annual = annual.reindex(range(FIRST_YEAR, LAST_YEAR + 1))
    if annual[SERIES].isna().any():
        sys.exit(f"ERROR: no index values for years {annual.index[annual[SERIES].isna()].tolist()}")

    short = annual[(annual["months_used"] < 12)]
    bad = short[(short.index < LAST_YEAR) | (short["months_used"] < MIN_MONTHS_LAST_YEAR)]
    if not bad.empty:
        sys.exit(f"ERROR: too few months behind these annual values:\n{bad}")
    for year, row in short.iterrows():
        print(f"  WARNING: {year} is the average of {int(row['months_used'])} of 12 months "
              f"(missing months have no published value); confirm this is acceptable for the base year.")

    out = annual.reset_index().rename(columns={"year": "observation_date"})
    out["observation_date"] = out["observation_date"].astype(int).astype(str) + "-01-01"
    out["months_used"] = out["months_used"].astype(int)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False, lineterminator="\n")
    print(f"acquire_cpi: {SERIES} annual averages, {len(out)} years -> {OUT.relative_to(ROOT)}")
    print(f"  {FIRST_YEAR}: {out[SERIES].iloc[0]}   {LAST_YEAR}: {out[SERIES].iloc[-1]}")


if __name__ == "__main__":
    main()
