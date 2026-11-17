"""Download ACS table B25040 (house heating fuel) for all states from the Census API.

1-year estimates (acs/acs1) for every year, except 2020: the standard 1-year file was not
released, so 2020 uses the 5-year estimates (acs/acs5). Estimates AND margins of error are kept.

Output: data/raw/acs_b25040.csv   (adds `year` and `estimate_type` = acs1 / acs5)
Needs:  environment variable CENSUS_API_KEY (free key: https://api.census.gov/data/key_signup.html;
        the key is emailed to you and must be activated with the link in that email)
"""
import os
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "raw" / "acs_b25040.csv"

FIRST_YEAR, LAST_YEAR = 2010, 2024
FIVE_YEAR_ONLY = {2020: "acs5"}
VAR_RE = re.compile(r"^B25040_\d{3}[EM]$")        # estimates and margins of error, not annotations
REQUIRED = ["B25040_001E", "B25040_001M", "B25040_004E", "B25040_004M"]


def request_variant(url, get, key):
    """One request; returns (table or None, diagnostic text)."""
    params = {"get": get, "for": "state:*"}
    if key:
        params["key"] = key
    try:
        resp = requests.get(url, params=params, timeout=90)
    except requests.RequestException as exc:          # exception text would contain the key
        return None, f"network error ({type(exc).__name__})"
    body = resp.text if resp.text else ""
    if key:
        body = body.replace(key, "<key>")
    if resp.status_code == 200:
        try:
            table = resp.json()
            if isinstance(table, list) and len(table) > 1:
                return table, ""
        except ValueError:
            pass
    ctype = resp.headers.get("Content-Type", "?")
    lowered = body.lower()
    if "missing key" in lowered or "invalid key" in lowered:
        return None, "the Census API rejected the key (missing or invalid; make sure you activated it from the email)"
    return None, f"HTTP {resp.status_code}, content-type {ctype}, body starts: {body[:200]!r}"


def fetch_year(year, key):
    survey = FIVE_YEAR_ONLY.get(year, "acs1")
    url = f"https://api.census.gov/data/{year}/acs/{survey}"
    attempts = [("group(B25040)", "NAME,group(B25040)"), ("core variables", "NAME," + ",".join(REQUIRED))]
    notes = []
    for label, get in attempts:
        table, diag = request_variant(url, get, key)
        if table is None:
            time.sleep(2)
            table, diag = request_variant(url, get, key)          # one retry
        if table is not None:
            df = pd.DataFrame(table[1:], columns=table[0])
            df = df.loc[:, ~df.columns.duplicated()]        # group(B25040) repeats NAME (and sometimes GEO_ID)
            vars_ = sorted(c for c in df.columns if VAR_RE.match(c))
            head = [c for c in ("GEO_ID", "NAME", "state") if c in df.columns]
            df = df[head + vars_].copy()
            df.insert(len(head), "year", str(year))
            df.insert(len(head) + 1, "estimate_type", survey)
            if label != "group(B25040)":
                print(f"  note: {year} used only the core variables ({label}); group() was not usable")
            return df
        notes.append(f"{label}: {diag}")
    sys.exit(f"ERROR: Census API gave no usable {survey} B25040 data for {year}.\n  " + "\n  ".join(notes))


def main():
    key = os.environ.get("CENSUS_API_KEY", "").strip()
    if not key:
        sys.exit(
            "ERROR: CENSUS_API_KEY is not set.\n"
            "Get a free key at https://api.census.gov/data/key_signup.html (it is emailed to you;\n"
            "click the activation link in that email), then set it:\n"
            "  macOS/Linux : export CENSUS_API_KEY=your_key\n"
            "  PowerShell  : $env:CENSUS_API_KEY='your_key'\n"
            "  cmd         : set CENSUS_API_KEY=your_key\n"
            "(Never commit the key.)"
        )
    frames = []
    for year in range(FIRST_YEAR, LAST_YEAR + 1):
        frames.append(fetch_year(year, key))
        print(f"  {year}: {len(frames[-1])} rows")
        time.sleep(0.3)
    df = pd.concat(frames, ignore_index=True)

    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        sys.exit(f"ERROR: expected variables missing from the response: {missing}")
    df = df.sort_values(["year", "NAME"]).reset_index(drop=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False, lineterminator="\n")
    by_type = df.groupby("estimate_type")["year"].unique().apply(lambda s: sorted(map(int, s))).to_dict()
    print(f"acquire_acs: {len(df)} rows, {df['NAME'].nunique()} geographies -> {OUT.relative_to(ROOT)}")
    print(f"  estimate types by year: {by_type}")


if __name__ == "__main__":
    main()
