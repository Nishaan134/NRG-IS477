from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parents[1]
MERGED = ROOT / "data" / "processed" / "merged_state_year.csv"
OUT = ROOT / "results" / "analysis"


def find_col(df, *keywords, exclude=()):
    """Return the first column whose name contains all keywords."""
    for c in df.columns:
        low = c.lower()
        if all(k in low for k in keywords) and not any(x in low for x in exclude):
            return c
    raise KeyError(f"No column containing {keywords}; columns are {list(df.columns)}")


def load():
    """Load the merged table with standard column names: state, year, price, income, share_pct, ..."""
    raw = pd.read_csv(MERGED)
    price = "real_price_cents_kwh" if "real_price_cents_kwh" in raw.columns else find_col(raw, "real", "price")
    share = "share_electric_heat" if "share_electric_heat" in raw.columns else find_col(
        raw, "share", exclude=("moe", "margin"))
    names = {find_col(raw, "state"): "state", find_col(raw, "year"): "year",
             price: "price", find_col(raw, "income"): "income", share: "share_raw"}
    try:
        names[find_col(raw, "moe")] = "share_moe_raw"
    except KeyError:
        pass
    try:  # nominal price, if present, for a sensitivity check
        names[find_col(raw, "price", exclude=("real", "index", "cpi"))] = "price_nominal"
    except KeyError:
        pass
    if "estimate_type" in raw.columns:
        names["estimate_type"] = "estimate_type"
    df = raw.rename(columns=names)
    scale = 100 if df["share_raw"].max() <= 1.0001 else 1  # work in percent of occupied homes
    df["share_pct"] = df["share_raw"] * scale
    if "share_moe_raw" in df.columns:
        df["share_moe_pct"] = df["share_moe_raw"] * scale
    df["log_price"] = np.log(df["price"])
    df["log_income"] = np.log(df["income"])
    if "price_nominal" in df.columns:
        df["log_price_nominal"] = np.log(df["price_nominal"])
    return df.sort_values(["state", "year"]).reset_index(drop=True)


def add_changes(df):
    """Year-over-year changes within state, only where the previous row is the previous year."""
    out = df.copy()
    consecutive = out.groupby("state")["year"].diff() == 1
    for col in ("share_pct", "log_price", "log_income"):
        out["d_" + col] = out.groupby("state")[col].diff().where(consecutive)
    return out


def md_table(df, floatfmt="{:.3f}"):
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for _, r in df.iterrows():
        cells = [floatfmt.format(v) if isinstance(v, (float, np.floating)) else str(v) for v in r]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def fit(formula, data, label, sample, price_term="log_price"):
    res = smf.ols(formula, data=data).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(data["state"])[0]})
    rows = []
    for term, name in ((price_term, "log_price"), ("log_income", "log_income")):
        coef = res.params[term]
        rows.append({"model": label, "sample": sample, "term": name, "coef": coef,
                     "pp_per_10pct_increase": coef * np.log(1.1), "std_err": res.bse[term],
                     "p_value": res.pvalues[term], "r_squared": res.rsquared, "n": int(res.nobs)})
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    df = add_changes(load())
    first, last = int(df["year"].min()), int(df["year"].max())
    lines = ["# Analysis summary", "",
             f"{len(df)} rows, {df['state'].nunique()} states, {first}-{last}. "
             "Share is the percent of occupied housing units heated by electricity. "
             "All results are associations, not causal effects.", ""]

    # ---- RQ1: variation across states and over time ------------------------------------------
    yearly = df.groupby("year").agg(
        price_mean=("price", "mean"), price_min=("price", "min"), price_max=("price", "max"),
        income_mean=("income", "mean"), income_min=("income", "min"), income_max=("income", "max"),
        share_mean=("share_pct", "mean"), share_min=("share_pct", "min"), share_max=("share_pct", "max"))
    yearly.round(3).to_csv(OUT / "rq1_yearly_summary.csv")

    wide = df.pivot(index="state", columns="year", values=["price", "income", "share_pct"])
    states = pd.DataFrame({
        "price_first": wide["price"][first], "price_last": wide["price"][last],
        "income_first": wide["income"][first], "income_last": wide["income"][last],
        "share_first": wide["share_pct"][first], "share_last": wide["share_pct"][last]})
    states["price_change_pct"] = (states["price_last"] / states["price_first"] - 1) * 100
    states["income_change_pct"] = (states["income_last"] / states["income_first"] - 1) * 100
    states["share_change_pp"] = states["share_last"] - states["share_first"]
    states.round(3).to_csv(OUT / "rq1_state_summary.csv")

    spread = pd.DataFrame({
        v: {"between_state_sd (state means)": df.groupby("state")[v].mean().std(),
            "within_state_sd (avg over states)": df.groupby("state")[v].std().mean()}
        for v in ("price", "income", "share_pct")}).T
    spread.round(3).to_csv(OUT / "rq1_between_vs_within_sd.csv")
    lines += ["## RQ1: variation", "",
              f"Mean real price: {yearly.loc[first, 'price_mean']:.2f} cents/kWh in {first}, "
              f"{yearly.loc[last, 'price_mean']:.2f} in {last}. Mean share: "
              f"{yearly.loc[first, 'share_mean']:.1f}% to {yearly.loc[last, 'share_mean']:.1f}%.",
              "", md_table(spread.reset_index().rename(columns={"index": "variable"})), ""]

    # ---- RQ2: within-year relationships ---------------------------------------------------------
    rows = []
    for y, g in df.groupby("year"):
        r = smf.ols("share_pct ~ log_price + log_income", data=g).fit(cov_type="HC1")
        rows.append({"year": y,
                     "spearman_share_price": g["share_pct"].corr(g["price"], method="spearman"),
                     "spearman_share_income": g["share_pct"].corr(g["income"], method="spearman"),
                     "spearman_price_income": g["price"].corr(g["income"], method="spearman"),
                     "coef_log_price": r.params["log_price"], "p_log_price": r.pvalues["log_price"],
                     "coef_log_income": r.params["log_income"], "p_log_income": r.pvalues["log_income"],
                     "r_squared": r.rsquared})
    xs = pd.DataFrame(rows).round(4)
    xs.to_csv(OUT / "rq2_cross_section_by_year.csv", index=False)
    lines += ["## RQ2: within-year (cross-state) relationships", "",
              "Per-year OLS of share on log price and log income, plus Spearman correlations: "
              "`rq2_cross_section_by_year.csv`. Years with price coefficient p<0.05: "
              f"{int((xs['p_log_price'] < 0.05).sum())} of {len(xs)}; income: "
              f"{int((xs['p_log_income'] < 0.05).sum())} of {len(xs)}.", ""]

    # ---- RQ3: changes over time and sensitivity ---------------------------------------------------
    models = []
    models += fit("share_pct ~ log_price + log_income", df, "pooled", "all years")
    models += fit("share_pct ~ log_price + log_income + C(year)", df, "year fixed effects", "all years")
    fe = "share_pct ~ log_price + log_income + C(state) + C(year)"
    models += fit(fe, df, "state + year fixed effects", "all years")
    diff = df.dropna(subset=["d_share_pct", "d_log_price", "d_log_income"])
    r = smf.ols("d_share_pct ~ d_log_price + d_log_income + C(year)", data=diff).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(diff["state"])[0]})
    for term, name in (("d_log_price", "log_price"), ("d_log_income", "log_income")):
        models.append({"model": "first differences + year effects", "sample": "consecutive years",
                       "term": name, "coef": r.params[term],
                       "pp_per_10pct_increase": r.params[term] * np.log(1.1), "std_err": r.bse[term],
                       "p_value": r.pvalues[term], "r_squared": r.rsquared, "n": int(r.nobs)})

    models += fit(fe, df[df["year"] != 2020], "sensitivity: state + year FE", "excluding 2020 (5-year ACS)")
    models += fit(fe, df[df["year"] >= 2017], "sensitivity: state + year FE", "2017 onward (CPS method change)")
    if "log_price_nominal" in df.columns:
        models += fit(fe.replace("log_price", "log_price_nominal"), df, "sensitivity: state + year FE",
                      "nominal price instead of real", price_term="log_price_nominal")
    if "share_moe_pct" in df.columns:
        rel = (df["share_moe_pct"] / df["share_pct"].replace(0, np.nan)).groupby(df["state"]).mean()
        noisy = rel.nlargest(10).index
        rel.sort_values(ascending=False).round(3).to_csv(OUT / "share_relative_moe_by_state.csv",
                                                         header=["mean_relative_moe"])
        models += fit(fe, df[~df["state"].isin(noisy)], "sensitivity: state + year FE",
                      "excluding 10 states with noisiest share")
        lines += [f"Mean relative margin of error of the share: {rel.mean():.2f}.", ""]
    reg = pd.DataFrame(models).round(4)
    reg.to_csv(OUT / "rq3_models.csv", index=False)
    show = reg[["model", "sample", "term", "pp_per_10pct_increase", "p_value", "n"]]
    lines += ["## RQ3: changes and sensitivity", "",
              "Effect columns are percentage points of share associated with a 10% higher price "
              "(or income). Standard errors are clustered by state.", "",
              md_table(show.rename(columns={"pp_per_10pct_increase": "pp_per_10pct"}), "{:.4f}"), ""]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()