import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "cpi.csv"
OUT = ROOT / "data" / "interim" / "cpi_clean.csv"


def main():
    if not RAW.exists():
        sys.exit(f"ERROR: missing input {RAW.relative_to(ROOT)} (run scripts/acquire_cpi.py first)")
    df = pd.read_csv(RAW, dtype=str)
    if df.shape[1] < 2:
        sys.exit(f"ERROR: {RAW.name} needs a date/year column and a value column")
    date_col, value_col = df.columns[0], df.columns[1]

    dates = df[date_col].str.strip()
    if dates.str.fullmatch(r"\d{4}").all():
        df["year"] = dates.astype(int)
        df["month"] = 1
    else:
        parsed = pd.to_datetime(dates, errors="coerce")
        if parsed.isna().any():
            sys.exit(f"ERROR: unparseable dates in {RAW.name}: {dates[parsed.isna()].tolist()[:5]}")
        df["year"], df["month"] = parsed.dt.year, parsed.dt.month
    df["cpi_index"] = pd.to_numeric(df[value_col].str.strip(), errors="coerce")
    df = df.dropna(subset=["cpi_index"])

    per_year = df.groupby("year")["month"].nunique()
    monthly = per_year.max() > 1
    if monthly:
        incomplete = per_year[per_year < 12]
        if not incomplete.empty:
            print(f"  WARNING: dropping incomplete years (fewer than 12 months): {incomplete.to_dict()}")
            df = df[~df["year"].isin(incomplete.index)]

    out = df.groupby("year", as_index=False)["cpi_index"].mean().round({"cpi_index": 4})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    print(f"clean_cpi: {'monthly' if monthly else 'annual'} source ({value_col}) -> "
          f"{len(out)} years {out['year'].min()}-{out['year'].max()}")


if __name__ == "__main__":
    main()
