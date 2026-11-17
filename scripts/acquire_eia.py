"""Download annual residential electricity prices for all states from the EIA API v2.

Output: data/raw/eia_residential_price.csv  (the API's columns, unchanged)
Needs:  environment variable EIA_API_KEY  (free key: https://www.eia.gov/opendata/register.php)
"""
import os
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "raw" / "eia_residential_price.csv"

URL = "https://api.eia.gov/v2/electricity/retail-sales/data/"
FIRST_YEAR, LAST_YEAR = 2010, 2025
PAGE_SIZE = 5000          # API maximum rows per request


def get_key():
    key = os.environ.get("EIA_API_KEY", "").strip()
    if not key:
        sys.exit(
            "ERROR: EIA_API_KEY is not set.\n"
            "Get a free key at https://www.eia.gov/opendata/register.php, then set it:\n"
            "  macOS/Linux : export EIA_API_KEY=your_key\n"
            "  PowerShell  : $env:EIA_API_KEY='your_key'\n"
            "  cmd         : set EIA_API_KEY=your_key\n"
            "(Never commit the key.)"
        )
    return key


def fetch_page(key, offset):
    params = {
        "api_key": key,
        "frequency": "annual",
        "data[0]": "price",
        "facets[sectorid][]": "RES",
        "start": str(FIRST_YEAR),
        "end": str(LAST_YEAR),
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
        "sort[1][column]": "stateid",
        "sort[1][direction]": "asc",
        "offset": offset,
        "length": PAGE_SIZE,
    }
    for attempt in range(3):
        try:
            resp = requests.get(URL, params=params, timeout=60)
        except requests.RequestException as exc:
            # do not print the exception text: it contains the URL, which contains the key
            if attempt == 2:
                sys.exit(f"ERROR: could not reach the EIA API ({type(exc).__name__}). Check your network.")
            time.sleep(2 * (attempt + 1))
            continue
        if resp.status_code == 200:
            return resp.json()["response"]
        if resp.status_code in (403, 401):
            sys.exit("ERROR: EIA rejected the API key (HTTP %d). Check EIA_API_KEY." % resp.status_code)
        if attempt == 2:
            sys.exit(f"ERROR: EIA API returned HTTP {resp.status_code}: {resp.text[:200]}")
        time.sleep(2 * (attempt + 1))


def main():
    key = get_key()
    records, offset, total = [], 0, None
    while True:
        page = fetch_page(key, offset)
        rows = page.get("data", [])
        total = int(page["total"])
        records.extend(rows)
        offset += len(rows)
        if not rows or offset >= total:
            break
    if len(records) != total:
        sys.exit(f"ERROR: API reported {total} rows but {len(records)} were downloaded")

    df = pd.DataFrame(records)
    needed = {"period", "stateid", "sectorid", "price", "price-units"}
    if not needed <= set(df.columns):
        sys.exit(f"ERROR: API response is missing columns {sorted(needed - set(df.columns))}")
    df = df.sort_values(["period", "stateid"]).reset_index(drop=True)   # stable row order -> stable checksum

    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False, lineterminator="\n")
    print(f"acquire_eia: {len(df)} rows, {df['stateid'].nunique()} geographies, "
          f"periods {df['period'].min()}-{df['period'].max()} -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
