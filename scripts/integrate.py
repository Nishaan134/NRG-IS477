import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
INTERIM = ROOT / "data" / "interim"
OUT = ROOT / "data" / "processed" / "merged_state_year.csv"
UNMATCHED = ROOT / "results" / "quality" / "unmatched_rows.csv"

FIRST_YEAR, LAST_YEAR = 2010, 2024
KEY = ["state", "year"]


def load(name):
    path = INTERIM / name
    if not path.exists():
        sys.exit(f"ERROR: missing input {path.relative_to(ROOT)}")
    return pd.read_csv(path)


def check_unique(df, name, key):
    dupes = df[df.duplicated(subset=key, keep=False)]
    if not dupes.empty:
        sys.exit(f"ERROR: duplicate {key} keys in {name}:\n{dupes}")


def main():
    eia, fred, acs, cpi = (load(f) for f in ("eia_clean.csv", "fred_clean.csv", "acs_clean.csv", "cpi_clean.csv"))
    sources = {"EIA": eia, "FRED": fred, "ACS": acs}
    for name, df in sources.items():
        check_unique(df, name, KEY)
    check_unique(cpi, "CPI", ["year"])

    base_year = int(fred["year"].max())
    if base_year not in set(cpi["year"]):
        sys.exit(f"ERROR: price index has no value for base year {base_year}")

    merged = (
        eia.merge(fred, on=KEY, how="inner", suffixes=("", "_fred"), validate="one_to_one")
           .merge(acs, on=KEY, how="inner", validate="one_to_one")
    )
    mismatch = merged[merged["state_abbr"] != merged["state_abbr_fred"]]
    if not mismatch.empty:
        sys.exit(f"ERROR: EIA and FRED disagree on state codes:\n{mismatch[KEY + ['state_abbr', 'state_abbr_fred']]}")
    merged = merged.drop(columns="state_abbr_fred")
    merged = merged[merged["year"].between(FIRST_YEAR, LAST_YEAR)]

    merged = merged.merge(cpi, on="year", how="left", validate="many_to_one")
    if merged["cpi_index"].isna().any():
        sys.exit(f"ERROR: no price index for years {sorted(merged.loc[merged['cpi_index'].isna(), 'year'].unique())}")
    base_cpi = cpi.loc[cpi["year"] == base_year, "cpi_index"].item()
    merged["real_price_cents_kwh"] = (merged["price_cents_kwh"] * base_cpi / merged["cpi_index"]).round(2)
    merged["dollar_base_year"] = base_year

    columns = [
        "state", "state_abbr", "year",
        "price_cents_kwh", "real_price_cents_kwh", "dollar_base_year",
        "real_median_income",
        "total_units", "total_units_moe", "units_electric_heat", "units_electric_heat_moe",
        "share_electric_heat", "share_electric_heat_moe", "estimate_type",
    ]
    merged = merged[columns].sort_values(KEY).reset_index(drop=True)

    kept = set(map(tuple, merged[KEY].to_numpy()))
    all_keys = {name: set(map(tuple, df[KEY].to_numpy())) for name, df in sources.items()}
    unmatched = []
    for name, df in sources.items():
        for state, year in df[KEY].itertuples(index=False):
            if (state, year) in kept:
                continue
            if not FIRST_YEAR <= year <= LAST_YEAR:
                reason = f"year outside {FIRST_YEAR}-{LAST_YEAR} study window"
            else:
                absent = [o for o in sources if o != name and (state, year) not in all_keys[o]]
                reason = "no matching row in " + ", ".join(absent)
            unmatched.append({"source": name, "state": state, "year": year, "reason": reason})
    unmatched = pd.DataFrame(unmatched, columns=["source", "state", "year", "reason"])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    UNMATCHED.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(OUT, index=False)
    unmatched.to_csv(UNMATCHED, index=False)

    print(f"integrate: EIA {len(eia)}, FRED {len(fred)}, ACS {len(acs)} rows -> {len(merged)} merged state-years")
    print(f"  {merged['state'].nunique()} states x {merged['year'].nunique()} years; prices deflated to {base_year} dollars")
    if unmatched.empty:
        print("  unmatched rows: none")
    else:
        print("  unmatched rows by source and reason:")
        print(unmatched.groupby(["source", "reason"]).size().to_string())


if __name__ == "__main__":
    main()
