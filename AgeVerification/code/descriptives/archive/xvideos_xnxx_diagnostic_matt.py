# Author: Matt Brown, assisted by Claude
# Created: 02/28/2026
# Purpose: Diagnostic figures for the mid-2024 break in xVideos and XNXX
#          intensive-margin usage in the Comscore panel.

"""
xVideos & XNXX Mid-2024 Diagnostic

Produces two figures:

  1. xvideos_xnxx_prepost_states.png
     Pre/post scatter plot (Apr–Jun 2024 vs Jul–Sep 2024) of winsorized
     min / active machine, one point per control state. Both xVideos and
     XNXX shown side by side. Points below the 45-degree line declined.

  2. xvideos_xnxx_demographics.png
     Winsorized min / active machine over time, split by (a) children
     present and (b) household income group. 2×2 grid (sites × demographics).

Usage: python code/descriptives/xvideos_xnxx_diagnostic_matt.py

Inputs:
- data/Aggregation/machine_panel/machine_aggregated_XVIDEOS.COM.parquet
- data/Aggregation/machine_panel/machine_aggregated_XNXX.COM.parquet
- data/ProcessComscore/full_demographics/full_machine_person_demos.parquet
- data/Aggregation/final_aggregated.csv
- raw/statelaws/statelaws_dates.csv

Outputs:
- output/descriptives/Aggregation/matt/xvideos_xnxx_prepost_states.png
- output/descriptives/Aggregation/matt/xvideos_xnxx_demographics.png
"""

import os
import sys
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

warnings.filterwarnings("ignore")

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

EXCLUDE_STATES = {"DC", "XX", "ZZ"}
SITES  = ["XVIDEOS.COM", "XNXX.COM"]
LABELS = {"XVIDEOS.COM": "xVideos", "XNXX.COM": "XNXX"}

BREAK     = pd.Timestamp("2023-08-01")
PRE_START = pd.Timestamp("2023-05-01")
PRE_END   = pd.Timestamp("2023-07-31")
POST_END  = pd.Timestamp("2023-10-31")

INCOME_MAP = {
    "HHI US: Less than 25k":  "Low (<40k)",
    "HHI US: 25k-39.999k":    "Low (<40k)",
    "HHI US: 40k-59.999k":    "Mid (40–100k)",
    "HHI US: 60k-74.999k":    "Mid (40–100k)",
    "HHI US: 75k-99.999k":    "Mid (40–100k)",
    "HHI US: 100k-149.999k":  "High (100k+)",
    "HHI US: 150k-199.999k":  "High (100k+)",
    "HHI US: 200k+":          "High (100k+)",
}

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

print("Loading demographics...")
demos_full = pd.read_parquet(
    os.path.join(project_root, "data", "ProcessComscore", "full_demographics",
                 "full_machine_person_demos.parquet"),
    columns=["machine_id", "state", "hh_income", "children_present"],
).drop_duplicates(subset="machine_id")
demos_full = demos_full[~demos_full["state"].isin(EXCLUDE_STATES)]
demos_full["income_grp"] = demos_full["hh_income"].map(INCOME_MAP)
control_states = set(demos_full["state"].unique()) - treated_states

# States with enough machines to show in state plot
presence = pd.read_parquet(os.path.join(data_dir, "machine_week_presence.parquet"))
presence = presence.merge(demos_full[["machine_id", "state"]], on="machine_id", how="left")
presence = presence[presence["state"].notna() & ~presence["state"].isin(EXCLUDE_STATES)]
denom = presence.groupby(["state", "week_of_sample"]).size().reset_index(name="machine_count")
denom["date"] = pd.to_datetime(denom["week_of_sample"].map(week_dates))
big_states = (
    denom[denom["state"].isin(control_states)]
    .groupby("state")["machine_count"].mean()
    .loc[lambda x: x >= 200]
    .index.tolist()
)
print(f"  Control states for state plot: {len(big_states)}")

# ============================================================================
# LOAD AND PROCESS SITES
# ============================================================================

def load_site(site):
    print(f"  Loading {site}...")
    mw = pd.read_parquet(
        os.path.join(data_dir, f"machine_aggregated_{site}.parquet"),
        columns=["machine_id", "week_of_sample", "total_duration"],
    )
    mw = mw[mw["total_duration"].notna()].copy()
    mw = mw.merge(demos_full, on="machine_id", how="left")
    mw = mw[
        mw["state"].notna()
        & ~mw["state"].isin(EXCLUDE_STATES)
        & mw["state"].isin(control_states)
    ].copy()
    p95 = mw.loc[mw["total_duration"] > 0, "total_duration"].quantile(0.95)
    mw["dur_w"] = mw["total_duration"].clip(upper=p95)
    mw["date"] = pd.to_datetime(mw["week_of_sample"].map(week_dates))
    return mw


print("Loading site panels...")
site_data = {s: load_site(s) for s in SITES}

# ============================================================================
# FIGURE 1: Pre/post scatter by state
# ============================================================================

def state_prepost(mw, big_states):
    """Mean winsorized min/active machine in pre and post windows, by state."""
    active = mw[mw["total_duration"] > 0].copy()
    by_sw = (
        active.groupby(["state", "date"])
        .agg(active_n=("machine_id", "nunique"), dur_w=("dur_w", "sum"))
        .reset_index()
    )
    by_sw["min_per_active"] = by_sw["dur_w"] / 60 / by_sw["active_n"]
    by_sw = by_sw[by_sw["state"].isin(big_states)]

    pre  = by_sw[(by_sw["date"] >= PRE_START) & (by_sw["date"] <= PRE_END)].groupby("state")["min_per_active"].mean()
    post = by_sw[(by_sw["date"] >= BREAK)     & (by_sw["date"] <= POST_END)].groupby("state")["min_per_active"].mean()
    return pd.DataFrame({"pre": pre, "post": post}).dropna()


print("\nComputing pre/post state means...")
fig, axes = plt.subplots(1, 2, figsize=(13, 6))

for j, site in enumerate(SITES):
    pp = state_prepost(site_data[site], big_states)
    ax = axes[j]

    lo = min(pp["pre"].min(), pp["post"].min()) * 0.85
    hi = max(pp["pre"].max(), pp["post"].max()) * 1.10
    ax.plot([lo, hi], [lo, hi], color="grey", linewidth=1, linestyle="--", zorder=0)

    colors = [COLOR_PALETTE[0] if row["post"] < row["pre"] else COLOR_PALETTE[1]
              for _, row in pp.iterrows()]
    ax.scatter(pp["pre"], pp["post"], color=colors, s=40, zorder=3)

    for st, row in pp.iterrows():
        ax.annotate(st, (row["pre"], row["post"]),
                    fontsize=6.5, xytext=(3, 2), textcoords="offset points")

    ax.set_xlabel("Apr–Jun 2024 mean (min / active machine)", fontsize=9)
    ax.set_ylabel("Jul–Sep 2024 mean (min / active machine)", fontsize=9) if j == 0 else None
    ax.set_title(f"{LABELS[site]}: pre vs post July 2024 by state\n"
                 f"(maroon = declined, navy = stable/up)", fontsize=10)
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)

plt.tight_layout()
out = os.path.join(output_dir, "xvideos_xnxx_prepost_states.png")
fig.savefig(out, dpi=150, bbox_inches="tight")
print(f"Saved: {out}")
plt.close(fig)

# ============================================================================
# FIGURE 2: Demographic breakdown time series
# ============================================================================

def intensity_by_group(mw, groupcol):
    active = mw[mw["total_duration"] > 0].copy()
    out = (
        active.groupby([groupcol, "date"])
        .agg(active_n=("machine_id", "nunique"), dur_w=("dur_w", "sum"))
        .reset_index()
    )
    out["min_per_active"] = out["dur_w"] / 60 / out["active_n"]
    return out

def fmt(ax):
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.tick_params(axis="x", rotation=30, labelsize=7)
    ax.axvline(BREAK, color="black", linewidth=0.8, linestyle="--", alpha=0.5)

children_colors = {"Children:Yes": COLOR_PALETTE[0], "Children:No": COLOR_PALETTE[1]}
income_order    = ["Low (<40k)", "Mid (40–100k)", "High (100k+)"]
income_colors   = dict(zip(income_order, COLOR_PALETTE[:3]))

print("Plotting demographic breakdown...")
fig, axes = plt.subplots(2, 2, figsize=(14, 9), sharey=False)

for j, site in enumerate(SITES):
    mw = site_data[site]

    # Row 0: children present
    ax = axes[0, j]
    grps = intensity_by_group(mw, "children_present")
    for val, color in children_colors.items():
        gdf = grps[grps["children_present"] == val].sort_values("date")
        if len(gdf) == 0:
            continue
        ax.plot(gdf["date"], gdf["min_per_active"], color=color, linewidth=1.4, label=val)
        pre  = gdf.loc[(gdf["date"] >= PRE_START) & (gdf["date"] <= PRE_END), "min_per_active"].mean()
        post = gdf.loc[(gdf["date"] >= BREAK)     & (gdf["date"] <= POST_END), "min_per_active"].mean()
        ax.annotate(f"→{post/pre:.2f}×", xy=(gdf["date"].iloc[-1], gdf["min_per_active"].iloc[-1]),
                    fontsize=7.5, color=color, xytext=(4, 0), textcoords="offset points")
    ax.set_title(f"{LABELS[site]}: by children present", fontsize=10)
    if j == 0:
        ax.set_ylabel("Winsorized min / active machine", fontsize=8)
    ax.legend(fontsize=8)
    fmt(ax)

    # Row 1: household income
    ax = axes[1, j]
    grps = intensity_by_group(mw, "income_grp")
    for val in income_order:
        gdf = grps[grps["income_grp"] == val].sort_values("date")
        if len(gdf) == 0:
            continue
        ax.plot(gdf["date"], gdf["min_per_active"], color=income_colors[val], linewidth=1.4, label=val)
        pre  = gdf.loc[(gdf["date"] >= PRE_START) & (gdf["date"] <= PRE_END), "min_per_active"].mean()
        post = gdf.loc[(gdf["date"] >= BREAK)     & (gdf["date"] <= POST_END), "min_per_active"].mean()
        ax.annotate(f"→{post/pre:.2f}×", xy=(gdf["date"].iloc[-1], gdf["min_per_active"].iloc[-1]),
                    fontsize=7.5, color=income_colors[val], xytext=(4, 0), textcoords="offset points")
    ax.set_title(f"{LABELS[site]}: by household income", fontsize=10)
    if j == 0:
        ax.set_ylabel("Winsorized min / active machine", fontsize=8)
    ax.legend(fontsize=8)
    fmt(ax)

fig.suptitle(
    "xVideos & XNXX: demographic breakdown of intensive margin\n"
    "(control states only, dashed = July 2024)",
    fontsize=11, y=1.01,
)
plt.tight_layout()
out = os.path.join(output_dir, "xvideos_xnxx_demographics.png")
fig.savefig(out, dpi=150, bbox_inches="tight")
print(f"Saved: {out}")
plt.close(fig)
