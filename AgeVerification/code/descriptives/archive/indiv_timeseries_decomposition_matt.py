# Author: Matt Brown, assisted by Claude
# Created: 02/27/2026
# Purpose: Decompose control-state XXX time series by site into
#          winsorized overall, panel size, % active, and winsorized intensity

"""
Individual-Level Time Series Decomposition by Site

For each of the 6 XXX site categories, produces a 4-row panel showing:
  Row 1: Winsorized min / machine / week (overall denominator)
  Row 2: Total panel machines in control states (k)
  Row 3: % of panel machines active on site that week
  Row 4: Winsorized min / active machine (intensive margin)

Each column has its own y-axis scale.

Usage: python code/descriptives/indiv_timeseries_decomposition_matt.py
       (Run on cluster — panel files are large)

Inputs:
- data/Aggregation/machine_panel/machine_week_presence.parquet
- data/Aggregation/machine_panel/machine_aggregated_{SITE}.parquet x6
- data/ProcessComscore/full_demographics/full_machine_person_demos.parquet
- data/Aggregation/final_aggregated.csv
- raw/statelaws/statelaws_dates.csv

Outputs:
- output/descriptives/Aggregation/matt/indiv_timeseries_decomposition.png
"""

import os
import sys
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

warnings.filterwarnings('ignore')

file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(file_dir, "..", ".."))
sys.path.insert(0, os.path.join(project_root, "code"))
from plot_style import apply_plot_style, COLOR_PALETTE

apply_plot_style()

# ============================================================================
# SETUP
# ============================================================================

data_dir   = os.path.join(project_root, "data", "Aggregation", "machine_panel")
output_dir = os.path.join(project_root, "output", "descriptives", "Aggregation", "matt")
os.makedirs(output_dir, exist_ok=True)

SITES = [
    "PORNHUB.COM",
    "CHATURBATE.COM",
    "XHAMSTER.COM",
    "XNXX.COM",
    "XVIDEOS.COM",
    "other_XXX_sites",
]
SITE_LABELS = {
    "PORNHUB.COM":     "Pornhub",
    "CHATURBATE.COM":  "Chaturbate",
    "XHAMSTER.COM":    "xHamster",
    "XNXX.COM":        "XNXX",
    "XVIDEOS.COM":     "xVideos",
    "other_XXX_sites": "Other XXX",
}

EXCLUDE_STATES = {"DC", "XX", "ZZ"}

# ============================================================================
# SHARED INPUTS
# ============================================================================

print("Loading state laws...")
laws = pd.read_csv(os.path.join(project_root, "raw", "statelaws", "statelaws_dates.csv"))
treated_states = set(laws.loc[laws["day_passed"].notna(), "state"])

week_dates = (
    pd.read_csv(
        os.path.join(project_root, "data", "Aggregation", "final_aggregated.csv"),
        usecols=["week_of_sample", "week_start_date"],
    )
    .drop_duplicates()
    .assign(week_start_date=lambda d: pd.to_datetime(d["week_start_date"]))
    .set_index("week_of_sample")["week_start_date"]
)

print("Loading machine demographics...")
demos = pd.read_parquet(
    os.path.join(project_root, "data", "ProcessComscore", "full_demographics",
                 "full_machine_person_demos.parquet"),
    columns=["machine_id", "state"],
).drop_duplicates(subset="machine_id")
demos = demos[~demos["state"].isin(EXCLUDE_STATES)]
control_states = set(demos["state"].unique()) - treated_states
print(f"  Control states: {len(control_states)}")

print("Loading machine_week_presence.parquet...")
presence = pd.read_parquet(os.path.join(data_dir, "machine_week_presence.parquet"))
presence = presence.merge(demos, on="machine_id", how="left")
presence = presence[presence["state"].notna() & ~presence["state"].isin(EXCLUDE_STATES)]

denom = presence.groupby(["state", "week_of_sample"]).size().reset_index(name="machine_count")
denom["date"] = pd.to_datetime(denom["week_of_sample"].map(week_dates))

ctrl_denom = denom[denom["state"].isin(control_states)]
nat_denom = ctrl_denom.groupby("date")["machine_count"].sum().reset_index()

# ============================================================================
# PER-SITE COMPUTATION
# ============================================================================

def fmt_date_axis(ax):
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.tick_params(axis="x", labelsize=7)

results = {}
for site in SITES:
    print(f"  {site}...")
    mw = pd.read_parquet(
        os.path.join(data_dir, f"machine_aggregated_{site}.parquet"),
        columns=["machine_id", "week_of_sample", "total_duration"],
    )
    mw = mw[mw["total_duration"].notna()].copy()
    mw = mw.merge(demos, on="machine_id", how="left")
    mw = mw[
        mw["state"].notna()
        & ~mw["state"].isin(EXCLUDE_STATES)
        & mw["state"].isin(control_states)
    ].copy()

    # p95 on nonzero machine-weeks
    p95 = mw.loc[mw["total_duration"] > 0, "total_duration"].quantile(0.95)
    mw["dur_w"] = mw["total_duration"].clip(upper=p95)

    # Row 0: winsorized min / machine / week (all panel machines as denominator)
    sw = (
        denom[denom["state"].isin(control_states)]
        .merge(
            mw.groupby(["state", "week_of_sample"])["dur_w"]
            .sum().reset_index(name="xxx_dur_w"),
            on=["state", "week_of_sample"], how="left",
        )
    )
    sw["xxx_dur_w"] = sw["xxx_dur_w"].fillna(0)
    nat_w = (
        sw.groupby("date")
        .apply(lambda g: g["xxx_dur_w"].sum() / 60 / g["machine_count"].sum(),
               include_groups=False)
        .reset_index(name="min_per_machine_w")
    )

    # Row 2: % active (machines with any usage that week)
    active_sw = (
        mw[mw["total_duration"] > 0]
        .groupby("week_of_sample")["machine_id"].nunique()
        .reset_index(name="active_machines")
    )
    active_sw["date"] = pd.to_datetime(active_sw["week_of_sample"].map(week_dates))
    combo = nat_denom.merge(active_sw, on="date")
    combo["pct_active"] = combo["active_machines"] / combo["machine_count"] * 100

    # Row 3: winsorized min / active machine
    active_dur_w = (
        mw[mw["total_duration"] > 0]
        .groupby("week_of_sample")
        .agg(active_machines=("machine_id", "nunique"), total_dur_w=("dur_w", "sum"))
        .reset_index()
    )
    active_dur_w["date"] = pd.to_datetime(active_dur_w["week_of_sample"].map(week_dates))
    active_dur_w["min_per_active_w"] = (
        active_dur_w["total_dur_w"] / 60 / active_dur_w["active_machines"]
    )

    results[site] = {
        "nat_w": nat_w,
        "combo": combo,
        "active_dur_w": active_dur_w,
        "p95_min": p95 / 60,
    }
    print(f"    p95={p95/60:.1f} min  mean_min/machine={nat_w['min_per_machine_w'].mean():.3f}")

# ============================================================================
# PLOT: 4 rows × 6 cols, independent y-axes
# ============================================================================

print("\nPlotting...")

ROW_LABELS = [
    "Winsorized\nmin / machine / week",
    "Total panel\nmachines (k)",
    "% panel active\non site",
    "Winsorized min /\nactive machine",
]

fig, axes = plt.subplots(4, 6, figsize=(22, 13), sharey=False)

for j, site in enumerate(SITES):
    c = COLOR_PALETTE[j % 5]
    r = results[site]

    ax = axes[0, j]
    ax.plot(r["nat_w"]["date"], r["nat_w"]["min_per_machine_w"], color=c, linewidth=1.2)
    ax.set_title(SITE_LABELS[site], fontsize=10)
    if j == 0:
        ax.set_ylabel(ROW_LABELS[0], fontsize=8)
    fmt_date_axis(ax)

    ax = axes[1, j]
    ax.plot(nat_denom["date"], nat_denom["machine_count"] / 1000, color="grey", linewidth=1.2)
    if j == 0:
        ax.set_ylabel(ROW_LABELS[1], fontsize=8)
    fmt_date_axis(ax)

    ax = axes[2, j]
    ax.plot(r["combo"]["date"], r["combo"]["pct_active"], color=c, linewidth=1.2)
    if j == 0:
        ax.set_ylabel(ROW_LABELS[2], fontsize=8)
    fmt_date_axis(ax)

    ax = axes[3, j]
    ax.plot(r["active_dur_w"]["date"], r["active_dur_w"]["min_per_active_w"], color=c, linewidth=1.2)
    if j == 0:
        ax.set_ylabel(ROW_LABELS[3], fontsize=8)
    fmt_date_axis(ax)

fig.suptitle(
    "Decomposition: winsorized overall · panel size · % active · winsorized intensity\n"
    "(control states only)",
    fontsize=12, y=1.01,
)
plt.tight_layout()

out_path = os.path.join(output_dir, "indiv_timeseries_decomposition.png")
fig.savefig(out_path, dpi=150, bbox_inches="tight")
print(f"\nSaved: {out_path}")
plt.close(fig)
