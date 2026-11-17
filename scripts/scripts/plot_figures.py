"""Figures for the analysis (one set per research question).

Reads  data/processed/merged_state_year.csv
Writes results/figures/*.png
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from analyze import ROOT, load

FIG = ROOT / "results" / "figures"
PANELS = [("price", "Real price (cents/kWh)"), ("income", "Real median income ($)"),
          ("share_pct", "Homes heated by electricity (%)")]


def trend_line(ax, x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    slope, intercept = np.polyfit(x[ok], y[ok], 1)
    xs = np.array([x[ok].min(), x[ok].max()])
    ax.plot(xs, intercept + slope * xs, color="tab:red", lw=1.5)


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    df = load()
    plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False})
    first, last = int(df["year"].min()), int(df["year"].max())

    # RQ1: each variable over time, mean with min-max band across states
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8))
    for ax, (col, label) in zip(axes, PANELS):
        g = df.groupby("year")[col]
        ax.fill_between(g.min().index, g.min(), g.max(), alpha=0.2)
        ax.plot(g.mean().index, g.mean(), lw=2)
        ax.set(xlabel="Year", ylabel=label)
    fig.suptitle(f"Mean across 50 states (line) and min-max range (band), {first}-{last}")
    fig.tight_layout(); fig.savefig(FIG / "rq1_trends.png"); plt.close(fig)

    # RQ2: cross-section in the latest year
    cs = df[df["year"] == last]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    for ax, (col, label) in zip(axes, PANELS[:2]):
        ax.scatter(cs[col], cs["share_pct"], s=35)
        trend_line(ax, cs[col].to_numpy(float), cs["share_pct"].to_numpy(float))
        ax.set(xlabel=label, ylabel=PANELS[2][1])
    fig.suptitle(f"Electric-heat share vs price and income across states, {last}")
    fig.tight_layout(); fig.savefig(FIG / "rq2_cross_section.png"); plt.close(fig)

    # RQ2: how the cross-state correlation moves year to year
    fig, ax = plt.subplots(figsize=(7, 4))
    for col, label in PANELS[:2]:
        ax.plot(sorted(df["year"].unique()),
                [g["share_pct"].corr(g[col], method="spearman") for _, g in df.groupby("year")],
                marker="o", label=f"share vs {label.split(' (')[0].lower()}")
    ax.axhline(0, color="gray", lw=0.8)
    ax.set(xlabel="Year", ylabel="Spearman correlation across states",
           title="Cross-state correlation with electric-heat share, by year")
    ax.legend(frameon=False)
    fig.tight_layout(); fig.savefig(FIG / "rq2_correlation_by_year.png"); plt.close(fig)

    # RQ3: change in each state from first to last year
    a, b = df[df["year"] == first].set_index("state"), df[df["year"] == last].set_index("state")
    d_share = b["share_pct"] - a["share_pct"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    for ax, col, label in ((axes[0], "price", "Change in real price (%)"),
                           (axes[1], "income", "Change in real income (%)")):
        x = ((b[col] / a[col] - 1) * 100).to_numpy(float)
        ax.scatter(x, d_share, s=35)
        trend_line(ax, x, d_share.to_numpy(float))
        ax.set(xlabel=label, ylabel="Change in electric-heat share (pp)")
    fig.suptitle(f"Change within each state, {first} to {last}")
    fig.tight_layout(); fig.savefig(FIG / "rq3_changes.png"); plt.close(fig)
    print("Wrote", sorted(p.name for p in FIG.glob("*.png")))


if __name__ == "__main__":
    main()