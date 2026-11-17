"""Pre-integration quality profile of the four raw files.

Reads data/raw/{eia_residential_price,fred_median_household_income,acs_b25040,cpi}.csv and writes
results/quality/pre_integration.md, covering accuracy, completeness, timeliness and consistency
for each source, cross-source consistency, a comparison of the re-acquired ACS data with the
original (legacy) ACS file, and a feasibility assessment for integration.

The report contains no timestamps, so rerunning on unchanged data gives an identical file.
"""
import re
import sys
from pathlib import Path

import pandas as pd

from state_codes import STATE_ABBRS, STATE_NAMES

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "results" / "quality" / "pre_integration.md"

FILES = {
    "eia": RAW / "eia_residential_price.csv",
    "fred": RAW / "fred_median_household_income.csv",
    "acs": RAW / "acs_b25040.csv",
    "cpi": RAW / "cpi.csv",
}
LEGACY_ACS = RAW / "legacy" / "ACS_states_annual_electricity_demand.csv"
LEGACY_EIA = RAW / "legacy" / "EIA_Average_retail_price_of_electricity.csv"

FIRST_YEAR, LAST_YEAR = 2010, 2025       # acquisition window
STUDY_LAST = 2024                        # last year all three state sources share
YOY_FLAG = 0.25                          # year-over-year change flagged for review
SERIES_RE = re.compile(r"^MEHOINUS([A-Z]{2})A672N$")


# ---------------------------------------------------------------- helpers
def md_table(df):
    lines = ["| " + " | ".join(map(str, df.columns)) + " |", "| " + " | ".join("---" for _ in df.columns) + " |"]
    lines += ["| " + " | ".join(str(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return lines


def load(path, label, script):
    if not path.exists():
        sys.exit(f"ERROR: missing input {path.relative_to(ROOT)} (run scripts/{script} first)")
    return pd.read_csv(path, dtype=str)


def need(df, cols, label):
    missing = [c for c in cols if c not in df.columns]
    if missing:
        sys.exit(f"ERROR: {label} is missing columns {missing}; found {list(df.columns)}")


def legacy_eia_values(keys):
    """Values for (state abbr, year) pairs from the original EIA browser export, if available."""
    if not keys or not LEGACY_EIA.exists():
        return {}
    try:
        old = pd.read_csv(LEGACY_EIA, skiprows=4, encoding="utf-8-sig", dtype=str)
        old["abbr"] = old["source key"].str.extract(r"ELEC\.PRICE\.([A-Z]{2})-RES\.A")
        found = {}
        for abbr, year in keys:
            row = old[old["abbr"] == abbr]
            if not row.empty and str(year) in old.columns:
                value = row[str(year)].iloc[0]
                if isinstance(value, str) and value.strip():
                    found[(abbr, year)] = value.strip()
        return found
    except Exception:
        return {}


def flag_jumps(wide, label, limit=8):
    """wide: index = year, columns = state. Returns markdown lines listing large year-over-year changes."""
    change = wide.sort_index().pct_change(fill_method=None)
    rows = []
    for state in change.columns:
        for year, v in change[state].items():
            if pd.notna(v) and abs(v) > YOY_FLAG:
                rows.append((state, int(year), f"{v:+.0%}"))
    if not rows:
        return [f"- No year-over-year change above {YOY_FLAG:.0%} in {label}."]
    shown = pd.DataFrame(rows[:limit], columns=["state", "year", "change"])
    return [f"- {len(rows)} state-years change by more than {YOY_FLAG:.0%} year over year (review, not necessarily errors):", ""] + md_table(shown) + [""]


# ---------------------------------------------------------------- per-source profiles
def profile_eia():
    df = load(FILES["eia"], "EIA", "acquire_eia.py")
    need(df, ["period", "stateid", "sectorid", "price", "price-units"], "EIA file")
    out = ["## 1. EIA residential electricity price", "", f"File: `{FILES['eia'].relative_to(ROOT)}`, {len(df)} rows.", ""]

    res = df[df["sectorid"].str.strip() == "RES"].copy()
    ids = res["stateid"].str.strip().str.upper()
    is_state = ids.isin(STATE_NAMES)
    extra = sorted(set(ids[~is_state]))
    st = res[is_state].copy()
    st["stateid"] = ids[is_state]
    st["year"] = pd.to_numeric(st["period"].str[:4], errors="coerce")
    st["price_num"] = pd.to_numeric(st["price"].str.replace(",", "", regex=False), errors="coerce")

    valid = st.dropna(subset=["year", "price_num"]).drop_duplicates(["stateid", "year"])
    years = sorted(valid["year"].astype(int).unique())
    expected = 50 * (LAST_YEAR - FIRST_YEAR + 1)
    dup = int(st.duplicated(["stateid", "year"]).sum())
    units = sorted(st["price-units"].str.strip().unique())
    q = valid["price_num"].describe()
    wide = valid.pivot(index="year", columns="stateid", values="price_num")

    miss = st[st["price_num"].isna()][["stateid", "year"]].dropna()
    miss_keys = sorted((r.stateid, int(r.year)) for r in miss.itertuples())
    legacy = legacy_eia_values(miss_keys)
    miss_txt = "; ".join(
        f"{s} {y}" + (f" (the original browser export has {legacy[(s, y)]} cents/kWh)" if (s, y) in legacy else "")
        for s, y in miss_keys) or "none"
    out += ["**Accuracy**", f"- Units: {units}. Price range {q['min']:.2f} to {q['max']:.2f} cents/kWh (median {q['50%']:.2f}).",
            f"- Non-numeric or missing prices: {len(miss_keys)} ({miss_txt})."]
    out += flag_jumps(wide, "EIA prices")
    out += ["", "**Completeness**",
            f"- {len(valid)} of {expected} expected state-years (50 states x {FIRST_YEAR}-{LAST_YEAR}) present; duplicate state-years: {dup}.",
            f"- Rows that are not one of the 50 states and must be filtered out in cleaning: {sorted(extra)}.", "",
            "**Timeliness**", f"- Years present: {years[0]}-{years[-1]} ({len(years)} years); annual frequency. The latest year may still be revised by EIA.", "",
            "**Consistency**", f"- State is identified by a 2-letter id; all 50 map to full names: {valid['stateid'].nunique() == 50}.",
            f"- One unit across all rows: {len(units) == 1}.", ""]
    keys = {(STATE_NAMES[s], int(y)) for s, y in zip(valid["stateid"], valid["year"])}
    return out, keys, years


def profile_fred():
    wide = load(FILES["fred"], "FRED", "acquire_fred.py")
    date_col = wide.columns[0]
    out = ["## 2. FRED real median household income", "", f"File: `{FILES['fred'].relative_to(ROOT)}`, {len(wide)} dates x {wide.shape[1] - 1} series.", ""]

    abbr = {c: SERIES_RE.match(c.strip()).group(1) for c in wide.columns[1:] if SERIES_RE.match(c.strip())}
    bad_cols = [c for c in wide.columns[1:] if c not in abbr]
    absent = sorted(set(STATE_NAMES) - set(abbr.values()))
    vals = wide[list(abbr)].apply(lambda s: pd.to_numeric(s.str.strip(), errors="coerce"))
    dots = int((wide[list(abbr)] == ".").sum().sum())
    years = pd.to_datetime(wide[date_col], errors="coerce").dt.year
    vals.index = years
    vals.columns = [abbr[c] for c in vals.columns]
    stacked = vals.stack()
    allv = stacked.describe()
    expected = 50 * len(set(years.dropna()))

    out += ["**Accuracy**", f"- Values range from {allv['min']:,.0f} to {allv['max']:,.0f} dollars (median {allv['50%']:,.0f}); all numeric after treating FRED's `.` as missing.",
            "- Units: constant dollars; FRED's series notes say 2000 onward is deflated with the C-CPI-U (see price-index section)."]
    out += flag_jumps(vals, "FRED income")
    out += ["", "**Completeness**", f"- {len(stacked)} of {expected} expected state-years present; `.` placeholders: {dots}.",
            f"- States without a series: {absent or 'none'} (DC has no FRED series). Unrecognized columns: {bad_cols or 'none'}.", "",
            "**Timeliness**", f"- Years {int(years.min())}-{int(years.max())}, annual. Census releases new data each September; the dollar base year moves with each release.", "",
            "**Consistency**", "- State appears only inside the series id (`MEHOINUS<ST>A672N`), so cleaning must reshape and parse it.",
            f"- Series ids match the 2-letter codes used by EIA: {not bad_cols}.", ""]
    keys = {(STATE_NAMES[s], int(y)) for y, row in vals.iterrows() for s, v in row.items() if pd.notna(v)}
    return out, keys, sorted(set(int(y) for y in years.dropna()))


def profile_acs():
    df = load(FILES["acs"], "ACS", "acquire_acs.py")
    cols = ["NAME", "year", "estimate_type", "B25040_001E", "B25040_001M", "B25040_004E", "B25040_004M"]
    need(df, cols, "ACS file")
    out = ["## 3. ACS B25040 house heating fuel", "", f"File: `{FILES['acs'].relative_to(ROOT)}`, {len(df)} rows.", ""]

    for c in cols[3:]:
        df[c + "_n"] = pd.to_numeric(df[c], errors="coerce")
    df["year_n"] = pd.to_numeric(df["year"], errors="coerce")
    df["NAME"] = df["NAME"].str.strip()
    extra = sorted(set(df["NAME"]) - set(STATE_ABBRS))
    st = df[df["NAME"].isin(STATE_ABBRS)].copy()
    sentinels = {c: int((df[c + "_n"] < 0).sum()) for c in cols[3:]}
    st["share"] = st["B25040_004E_n"] / st["B25040_001E_n"]
    over = int((st["B25040_004E_n"] > st["B25040_001E_n"]).sum())
    dup = int(st.duplicated(["NAME", "year"]).sum())
    years = sorted(st["year_n"].dropna().astype(int).unique())
    types = st.groupby("estimate_type")["year_n"].apply(lambda s: sorted(int(y) for y in s.unique())).to_dict()
    expected = 50 * (STUDY_LAST - FIRST_YEAR + 1)
    rel_moe = (st["B25040_004M_n"].where(st["B25040_004M_n"] >= 0) / st["B25040_004E_n"]).dropna()
    wide = st.pivot(index="year_n", columns="NAME", values="share")

    out += ["**Accuracy**", f"- Electric-heat share ranges {st['share'].min():.1%} to {st['share'].max():.1%}; rows where electric units exceed total units: {over}.",
            f"- Margin of error of the electric-heat count is a median {rel_moe.median():.1%} of the estimate (max {rel_moe.max():.1%}); small states are noisier."]
    out += flag_jumps(wide, "ACS electric-heat share")
    out += ["", "**Completeness**", f"- {len(st.drop_duplicates(['NAME', 'year']))} of {expected} expected state-years (50 states x {FIRST_YEAR}-{STUDY_LAST}); duplicates: {dup}.",
            f"- Census sentinel (negative) values per column: {sentinels}.",
            f"- Geographies that are not one of the 50 states and must be dropped: {extra}.", "",
            "**Timeliness**", f"- Years {years[0]}-{years[-1]}; ACS lags EIA and FRED by one year, so the study window ends in {STUDY_LAST}.", "",
            "**Consistency**", f"- Estimate type by year: {types}. 2020 is a 5-year estimate because no standard 1-year file was released, so it is not strictly comparable and is flagged.",
            "- State is a full name (matches the project's state table); EIA and FRED use 2-letter codes.", ""]
    keys = {(n, int(y)) for n, y in zip(st["NAME"], st["year_n"]) if pd.notna(y)}
    return out, keys, years, st


def profile_cpi():
    df = load(FILES["cpi"], "CPI", "acquire_cpi.py")
    out = ["## 4. Price index (C-CPI-U)", "", f"File: `{FILES['cpi'].relative_to(ROOT)}`, {len(df)} rows.", ""]
    if df.shape[1] < 2:
        sys.exit("ERROR: cpi.csv needs a date column and a value column")
    date_col, val_col = df.columns[:2]
    year = pd.to_datetime(df[date_col], errors="coerce").dt.year
    val = pd.to_numeric(df[val_col].str.strip(), errors="coerce")
    ok = pd.DataFrame({"year": year, "v": val}).dropna()
    inc = ok["v"].diff().dropna()
    infl = ok.set_index("year")["v"].pct_change().dropna()
    out += ["**Accuracy**", f"- Series `{val_col}`; index values {ok['v'].min():.2f} to {ok['v'].max():.2f}; year-over-year inflation {infl.min():+.1%} to {infl.max():+.1%}.",
            ("- Index rises every year." if (inc > 0).all() else
             f"- Year-over-year declines in {[int(y) for y in ok.set_index('year')['v'].diff().dropna().loc[lambda s: s < 0].index]} "
             "(small deflation episodes are possible for a chained CPI; reported for review, not treated as errors)."), "",
            "**Completeness**", f"- {len(ok)} annual values; missing or non-numeric: {int(len(df) - len(ok))}; years present {int(ok['year'].min())}-{int(ok['year'].max())}.",
            *( [f"- Months averaged per year: {int(mu.min())}-{int(mu.max())}; years built from fewer than 12 months: {sorted(df.loc[mu < 12, date_col].str[:4].tolist()) or 'none'}."]
               if "months_used" in df.columns and not (mu := pd.to_numeric(df["months_used"], errors="coerce")).isna().all() else [] ), "",
            "**Timeliness**", "- The latest annual value may be built from fewer than 12 months of data if the source has gaps; check before treating it as final.", "",
            "**Consistency**", "- Same C-CPI-U deflator family as the FRED income series, so prices and income end up in comparable constant dollars.", ""]
    return out, sorted(int(y) for y in ok["year"].unique())


def legacy_comparison(acs_states):
    out = ["## 5. Re-acquired ACS vs. the original ACS file", ""]
    if not LEGACY_ACS.exists():
        return out + [f"The original file `{LEGACY_ACS.relative_to(ROOT)}` was not found; run `git mv` to place it there to enable this comparison.", ""]
    old = pd.read_csv(LEGACY_ACS)
    need(old, ["state", "year", "total_units", "units_electricity"], "legacy ACS file")
    new = pd.DataFrame({"state": acs_states["NAME"], "year": acs_states["year_n"].astype("Int64"),
                        "new_total": acs_states["B25040_001E_n"], "new_electric": acs_states["B25040_004E_n"]})
    m = old.assign(year=old["year"].astype("Int64")).merge(new, on=["state", "year"], how="outer", indicator=True)
    both = m[m["_merge"] == "both"]
    same = both[(both["total_units"] == both["new_total"]) & (both["units_electricity"] == both["new_electric"])]
    diff = both.drop(same.index)
    out += [f"- State-years in both files: {len(both)}; identical total and electric counts: {len(same)}; different: {len(diff)}.",
            f"- Only in the original file: {int((m['_merge'] == 'left_only').sum())}; only in the new file: {int((m['_merge'] == 'right_only').sum())}.", ""]
    if len(diff):
        d = diff[["state", "year", "total_units", "new_total", "units_electricity", "new_electric"]].head(10).copy()
        d.columns = ["state", "year", "old total", "new total", "old electric", "new electric"]
        out += ["First differences:", ""] + md_table(d) + [""]
        by_year = diff.groupby("year").size().to_dict()
        out += [f"- Differences by year: { {int(k): int(v) for k, v in by_year.items()} }.", ""]
    out += ["The new file adds margins of error and an explicit `estimate_type`; the original had neither.", ""]
    return out


# ---------------------------------------------------------------- main
def main():
    eia, eia_keys, eia_years = profile_eia()
    fred, fred_keys, fred_years = profile_fred()
    acs, acs_keys, acs_years, acs_states = profile_acs()
    cpi, cpi_years = profile_cpi()

    window = range(FIRST_YEAR, STUDY_LAST + 1)
    joint = {k for k in eia_keys & fred_keys & acs_keys if k[1] in window}
    expected = 50 * len(window)
    cross = ["## 6. Cross-source consistency and integration feasibility", ""]
    cross += md_table(pd.DataFrame([
        ["EIA", f"{eia_years[0]}-{eia_years[-1]}", len({k[0] for k in eia_keys})],
        ["FRED", f"{fred_years[0]}-{fred_years[-1]}", len({k[0] for k in fred_keys})],
        ["ACS", f"{acs_years[0]}-{acs_years[-1]}", len({k[0] for k in acs_keys})],
        ["C-CPI-U", f"{cpi_years[0]}-{cpi_years[-1]}", "n/a (by year)"],
    ], columns=["source", "years", "states"]))
    cross += ["", f"- Join key `(state, year)`: {len(joint)} of {expected} expected state-years ({FIRST_YEAR}-{STUDY_LAST}) exist in all three state sources.",
              f"- EIA and FRED use 2-letter codes and ACS uses full names; the shared lookup `scripts/state_codes.py` maps all 50 states to one set of names.",
              "- Geographies outside the 50 states (EIA aggregates and DC, ACS DC and Puerto Rico) have no FRED counterpart and are dropped.",
              f"- Price index covers {cpi_years[0]}-{cpi_years[-1]}, so every study year can be deflated.", "",
              "**Why integration is feasible:** the three state sources share a common key and overlapping coverage, differ only in "
              "representation (wide vs. long, codes vs. names, text vs. numbers), and every difference found above can be resolved "
              "deterministically in cleaning. The one real comparability caveat is the 2020 ACS 5-year estimate, which is carried through with a flag.", ""]

    header = ["# Pre-integration quality report", "", "Generated by `scripts/profile_raw.py` from the files in `data/raw/`. "
              "Findings below drive the cleaning rules in `scripts/clean_*.py`.", ""]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(header + eia + fred + acs + cpi + legacy_comparison(acs_states) + cross) + "\n", encoding="utf-8")
    print(f"profile_raw: wrote {OUT.relative_to(ROOT)} ({len(joint)}/{expected} joint state-years)")


if __name__ == "__main__":
    main()
