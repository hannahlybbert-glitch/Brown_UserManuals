# Author: Matt Brown, assisted by Claude
# Created: 02/27/2026
# Purpose: Control state time series — 4 iterative aggregation refinements
#          starting from individual machine-week panel

"""
Individual-Level Control State Time Series

Re-derives the control state time series from the machine-week panel,
showing cumulative effect of 4 aggregation refinements in a 2x2 grid:

  Panel 1: Step 0 (agg data, dashed) vs Step 1 (individual data, solid)
           Sanity check — should be near-identical.
  Panel 2: Step 1 (unweighted state mean) vs Step 2 (weighted by machine count)
  Panel 3: Step 2 vs Step 3 (p95-winsorized before aggregating)
  Panel 4: Step 3 vs Step 4 (within-machine FE demeaning)

Usage: python code/descriptives/indiv_timeseries_control_matt.py
       (Run on cluster — panel files are large)

Inputs:
- data/Aggregation/machine_panel/machine_week_presence.parquet
- data/Aggregation/machine_panel/machine_aggregated_{SITE}.parquet x6
- data/ProcessComscore/full_demographics/full_machine_person_demos.parquet
- data/Aggregation/final_aggregated.csv
- raw/statelaws/statelaws_dates.csv

Outputs:
- output/descriptives/Aggregation/matt/indiv_timeseries_control_versions.png
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

EXCLUDE_STATES = {"DC", "XX", "ZZ"}

# ============================================================================
# WEEK → DATE MAPPING
# ============================================================================

week_dates = (
    pd.read_csv(
        os.path.join(project_root, "data", "Aggregation", "final_aggregated.csv"),
        usecols=["week_of_sample", "week_start_date"],
    )
    .drop_duplicates()
    .assign(week_start_date=lambda d: pd.to_datetime(d["week_start_date"]))
    .set_index("week_of_sample")["week_start_date"]
)

# ============================================================================
# STATE LISTS
# ============================================================================

print("Loading state laws...")
laws = pd.read_csv(os.path.join(project_root, "raw", "statelaws", "statelaws_dates.csv"))
treated_states = set(laws.loc[laws["day_passed"].notna(), "state"].tolist())

# ============================================================================
# STEP 0: Baseline from final_aggregated.csv (replicates aggregation_descriptives_matt.py)
# ============================================================================

print("Step 0: loading final_aggregated.csv baseline...")

XXX_CATEGORIES = [
    "PORNHUB.COM", "XVIDEOS.COM", "XHAMSTER.COM",
    "XNXX.COM", "CHATURBATE.COM", "other_XXX_sites",
]

df_full = pd.read_csv(
    os.path.join(project_root, "data", "Aggregation", "final_aggregated.csv")
)
df_full["week_start_date"] = pd.to_datetime(df_full["week_start_date"])
df_full = df_full[~df_full["state"].isin(EXCLUDE_STATES)].copy()

# All states present in the agg data
all_agg_states = set(df_full["state"].unique())
control_states_agg = all_agg_states - treated_states

machines_full = (
    df_full.groupby(["state", "week_start_date"])["all_machine_count"]
    .first().reset_index()
)
xxx_dur_full = (
    df_full[df_full["coarse_category"].isin(XXX_CATEGORIES)]
    .groupby(["state", "week_start_date"])["total_duration_seconds"]
    .sum().reset_index()
    .rename(columns={"total_duration_seconds": "xxx_duration"})
)
sw_full = machines_full.merge(xxx_dur_full, on=["state", "week_start_date"])
sw_full = sw_full[sw_full["all_machine_count"] > 0].copy()
sw_full["min_per_machine"] = sw_full["xxx_duration"] / 60 / sw_full["all_machine_count"]

step0 = (
    sw_full[sw_full["state"].isin(control_states_agg)]
    .groupby("week_start_date")["min_per_machine"]
    .mean()
    .reset_index()
    .rename(columns={"min_per_machine": "ctrl", "week_start_date": "date"})
    .sort_values("date")
)

print(f"  Step 0: {len(step0)} weeks, mean={step0['ctrl'].mean():.3f} min/machine/week")

# ============================================================================
# LOAD INDIVIDUAL DATA
# ============================================================================

print("Loading machine demographics (state mapping)...")
demos = pd.read_parquet(
    os.path.join(project_root, "data", "ProcessComscore", "full_demographics",
                 "full_machine_person_demos.parquet"),
    columns=["machine_id", "state"],
).drop_duplicates(subset="machine_id")
demos = demos[~demos["state"].isin(EXCLUDE_STATES)].copy()

# Control states from individual data
all_indiv_states = set(demos["state"].unique())
control_states_indiv = all_indiv_states - treated_states
print(f"  Control states in individual data: {len(control_states_indiv)}")

print("Loading machine_week_presence.parquet...")
presence = pd.read_parquet(os.path.join(data_dir, "machine_week_presence.parquet"))
# Join state
presence = presence.merge(demos[["machine_id", "state"]], on="machine_id", how="left")
presence = presence[presence["state"].notna()].copy()
presence = presence[~presence["state"].isin(EXCLUDE_STATES)].copy()

# Denominator: count of machines in panel per (state, week)
denom = (
    presence.groupby(["state", "week_of_sample"])
    .size()
    .reset_index(name="machine_count")
)

print("Loading and concatenating XXX site parquets...")
site_frames = []
for site in SITES:
    fname = os.path.join(data_dir, f"machine_aggregated_{site}.parquet")
    df = pd.read_parquet(fname, columns=["machine_id", "week_of_sample", "total_duration"])
    site_frames.append(df)

panel = pd.concat(site_frames, ignore_index=True)
del site_frames

# Sum across sites per machine-week (null = absent from that site's parquet → skip)
panel = panel[panel["total_duration"].notna()].copy()
machine_week = (
    panel.groupby(["machine_id", "week_of_sample"])["total_duration"]
    .sum()
    .reset_index()
)
del panel

# Join state
machine_week = machine_week.merge(demos[["machine_id", "state"]], on="machine_id", how="left")
machine_week = machine_week[machine_week["state"].notna()].copy()
machine_week = machine_week[~machine_week["state"].isin(EXCLUDE_STATES)].copy()

print(f"  Machine-weeks with nonzero duration: {len(machine_week):,}")

# ============================================================================
# STEP 1: Literal replication — unweighted mean across control states
# ============================================================================

print("Step 1: unweighted mean...")

sw1 = (
    machine_week.groupby(["state", "week_of_sample"])["total_duration"]
    .sum()
    .reset_index(name="xxx_duration")
    .merge(denom, on=["state", "week_of_sample"])
)
sw1["min_per_machine"] = sw1["xxx_duration"] / 60 / sw1["machine_count"]

step1 = (
    sw1[sw1["state"].isin(control_states_indiv)]
    .groupby("week_of_sample")["min_per_machine"]
    .mean()
    .reset_index()
)
step1["date"] = step1["week_of_sample"].map(week_dates)
step1 = step1.sort_values("date").rename(columns={"min_per_machine": "ctrl"})

print(f"  Step 1: {len(step1)} weeks, mean={step1['ctrl'].mean():.3f} min/machine/week")

# ============================================================================
# STEP 2: Weighted by state machine count
# ============================================================================

print("Step 2: weighted by machine count...")

ctrl_sw2 = sw1[sw1["state"].isin(control_states_indiv)].copy()
agg2 = (
    ctrl_sw2.groupby("week_of_sample")
    .apply(lambda g: g["xxx_duration"].sum() / 60 / g["machine_count"].sum())
    .reset_index(name="ctrl")
)
agg2["date"] = agg2["week_of_sample"].map(week_dates)
step2 = agg2.sort_values("date")

print(f"  Step 2: {len(step2)} weeks, mean={step2['ctrl'].mean():.3f} min/machine/week")

# ============================================================================
# STEP 3: Winsorize at p95 (pooled across all XXX machine-weeks), then aggregate
# ============================================================================

print("Step 3: p95 winsorization...")

# Recompute from machine_week with winsorization
# p95 computed over nonzero observations only, pooled across sites (consistent with
# indiv_descriptives_timeseries_matt.py which also excludes zero-duration machine-weeks)
p95 = machine_week.loc[machine_week["total_duration"] > 0, "total_duration"].quantile(0.95)
print(f"  p95 cap (seconds): {p95:.1f}  ({p95/60:.1f} min)")

machine_week_w = machine_week.copy()
machine_week_w["total_duration"] = machine_week_w["total_duration"].clip(upper=p95)

sw3 = (
    machine_week_w.groupby(["state", "week_of_sample"])["total_duration"]
    .sum()
    .reset_index(name="xxx_duration")
    .merge(denom, on=["state", "week_of_sample"])
)

ctrl_sw3 = sw3[sw3["state"].isin(control_states_indiv)].copy()
agg3 = (
    ctrl_sw3.groupby("week_of_sample")
    .apply(lambda g: g["xxx_duration"].sum() / 60 / g["machine_count"].sum())
    .reset_index(name="ctrl")
)
agg3["date"] = agg3["week_of_sample"].map(week_dates)
step3 = agg3.sort_values("date")

print(f"  Step 3: {len(step3)} weeks, mean={step3['ctrl'].mean():.3f} min/machine/week")

# ============================================================================
# STEP 4: Within-machine FE demeaning
# ============================================================================

print("Step 4: within-machine FE demeaning...")

machine_means = (
    machine_week_w.groupby("machine_id")["total_duration"]
    .mean()
    .rename("machine_mean")
)
machine_week_fe = machine_week_w.join(machine_means, on="machine_id")
machine_week_fe["duration_demeaned"] = (
    machine_week_fe["total_duration"] - machine_week_fe["machine_mean"]
)

# Aggregate demeaned values to (state, week)
sw4 = (
    machine_week_fe.groupby(["state", "week_of_sample"])["duration_demeaned"]
    .sum()
    .reset_index(name="xxx_duration_dm")
    .merge(denom, on=["state", "week_of_sample"])
)

ctrl_sw4 = sw4[sw4["state"].isin(control_states_indiv)].copy()
agg4 = (
    ctrl_sw4.groupby("week_of_sample")
    .apply(lambda g: g["xxx_duration_dm"].sum() / 60 / g["machine_count"].sum())
    .reset_index(name="ctrl_dm")
)
agg4["date"] = agg4["week_of_sample"].map(week_dates)
agg4 = agg4.sort_values("date")

# Grand-mean level from Step 3 (baseline period: all weeks — re-center)
grand_mean_level = step3["ctrl"].mean()
agg4["ctrl"] = agg4["ctrl_dm"] + grand_mean_level
step4 = agg4[["date", "ctrl"]].copy()

print(f"  Step 4: {len(step4)} weeks, mean={step4['ctrl'].mean():.3f} min/machine/week")

# ============================================================================
# PLOT: 2×2 grid
# ============================================================================

print("Plotting...")

color_before = COLOR_PALETTE[1]  # navy (navy is index 1 per plan)
color_after  = COLOR_PALETTE[0]  # maroon

# Axis date formatter helper
def fmt_date_axis(ax):
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.tick_params(axis="x", rotation=0)

fig, axes = plt.subplots(2, 2, figsize=(14, 9), sharey=False)

# ------ Panel 1: Step 0 vs Step 1 ------
ax = axes[0, 0]
ax.plot(step0["date"], step0["ctrl"],
        color=color_before, linewidth=1.4, linestyle="--", label="Step 0 (agg data)")
ax.plot(step1["date"], step1["ctrl"],
        color=color_after,  linewidth=1.4, label="Step 1 (individual data)")
ax.set_title("Panel 1: Agg data vs Individual replication", fontsize=11)
ax.set_ylabel("Min / machine / week")
ax.legend(fontsize=9)
fmt_date_axis(ax)

# ------ Panel 2: Step 1 vs Step 2 ------
ax = axes[0, 1]
ax.plot(step1["date"], step1["ctrl"],
        color=color_before, linewidth=1.4, linestyle="--", label="Step 1 (unweighted)")
ax.plot(step2["date"], step2["ctrl"],
        color=color_after,  linewidth=1.4, label="Step 2 (weighted by N machines)")
ax.set_title("Panel 2: Unweighted vs Weighted", fontsize=11)
ax.legend(fontsize=9)
fmt_date_axis(ax)

# ------ Panel 3: Step 2 vs Step 3 ------
ax = axes[1, 0]
ax.plot(step2["date"], step2["ctrl"],
        color=color_before, linewidth=1.4, linestyle="--", label="Step 2 (weighted)")
ax.plot(step3["date"], step3["ctrl"],
        color=color_after,  linewidth=1.4, label="Step 3 (p95 winsorized)")
ax.set_title("Panel 3: Weighted vs Winsorized", fontsize=11)
ax.set_ylabel("Min / machine / week")
ax.legend(fontsize=9)
fmt_date_axis(ax)

# ------ Panel 4: Step 3 vs Step 4 ------
ax = axes[1, 1]
ax.plot(step3["date"], step3["ctrl"],
        color=color_before, linewidth=1.4, linestyle="--", label="Step 3 (winsorized)")
ax.plot(step4["date"], step4["ctrl"],
        color=color_after,  linewidth=1.4, label="Step 4 (machine FE demeaned)")
ax.set_title("Panel 4: Winsorized vs Machine-FE corrected", fontsize=11)
ax.legend(fontsize=9)
fmt_date_axis(ax)

fig.suptitle(
    "Control state time series — iterative aggregation refinements\n"
    "(min / machine / week, all XXX sites pooled)",
    fontsize=13, y=1.01,
)
plt.tight_layout()

out_path = os.path.join(output_dir, "indiv_timeseries_control_versions.png")
fig.savefig(out_path, dpi=300, bbox_inches="tight")
print(f"\nSaved: {out_path}")
plt.close(fig)

# ============================================================================
# PLOT A: All 5 steps on a single axis (pooled XXX)
# ============================================================================

print("\nPlotting all steps on single axes...")

COLORS5 = COLOR_PALETTE[:5]
steps_meta = [
    (step0, "Step 0: State-level aggregates (previous file)",               "--", COLORS5[1]),
    (step1, "Step 1: Individual file, each state equally weighted",          "-",  COLORS5[0]),
    (step2, "Step 2: Weight states by number of machines",                   "-",  COLORS5[2]),
    (step3, "Step 3: Winsorize machine-week duration at p95 of nonzero\n"
            "        machine-weeks (pooled across XXX sites)",               "-",  COLORS5[3]),
    (step4, "Step 4: Subtract each machine's time-average duration,\n"
            "        re-center to Step 3 grand mean",                        "-",  COLORS5[4]),
]

fig, ax = plt.subplots(figsize=(12, 5))
for df, label, ls, color in steps_meta:
    ax.plot(df["date"], df["ctrl"], color=color, linewidth=1.4, linestyle=ls, label=label)
ax.set_title(
    "Control state time series — all aggregation steps\n(min / machine / week, all XXX pooled)",
    fontsize=12,
)
ax.set_ylabel("Min / machine / week")
ax.legend(fontsize=9)
fmt_date_axis(ax)
plt.tight_layout()

out_path = os.path.join(output_dir, "indiv_timeseries_control_allsteps.png")
fig.savefig(out_path, dpi=300, bbox_inches="tight")
print(f"Saved: {out_path}")
plt.close(fig)

# ============================================================================
# STEPS 0–4 BY SITE
# ============================================================================

SITE_LABELS = {
    "PORNHUB.COM":     "Pornhub",
    "CHATURBATE.COM":  "Chaturbate",
    "XHAMSTER.COM":    "xHamster",
    "XNXX.COM":        "XNXX",
    "XVIDEOS.COM":     "xVideos",
    "other_XXX_sites": "Other XXX",
}

print("\nComputing steps 0–4 by site...")
site_steps = {}

for site in SITES:
    print(f"  {site}...")

    # --- Step 0: from final_aggregated.csv ---
    xxx_dur_site = (
        df_full[df_full["coarse_category"] == site]
        .groupby(["state", "week_start_date"])["total_duration_seconds"]
        .sum().reset_index()
        .rename(columns={"total_duration_seconds": "xxx_duration"})
    )
    sw0 = machines_full.merge(xxx_dur_site, on=["state", "week_start_date"], how="left")
    sw0["xxx_duration"] = sw0["xxx_duration"].fillna(0)
    sw0 = sw0[sw0["all_machine_count"] > 0].copy()
    sw0["min_per_machine"] = sw0["xxx_duration"] / 60 / sw0["all_machine_count"]
    s0 = (
        sw0[sw0["state"].isin(control_states_agg)]
        .groupby("week_start_date")["min_per_machine"].mean()
        .reset_index()
        .rename(columns={"min_per_machine": "ctrl", "week_start_date": "date"})
        .sort_values("date")
    )

    # --- Load this site's individual panel ---
    fname = os.path.join(data_dir, f"machine_aggregated_{site}.parquet")
    mw_site = pd.read_parquet(fname, columns=["machine_id", "week_of_sample", "total_duration"])
    mw_site = mw_site[mw_site["total_duration"].notna()].copy()
    mw_site = mw_site.merge(demos[["machine_id", "state"]], on="machine_id", how="left")
    mw_site = mw_site[mw_site["state"].notna() & ~mw_site["state"].isin(EXCLUDE_STATES)].copy()

    # Step 1: unweighted state mean
    sw1 = (
        denom.merge(
            mw_site.groupby(["state", "week_of_sample"])["total_duration"]
            .sum().reset_index(name="xxx_duration"),
            on=["state", "week_of_sample"], how="left",
        )
    )
    sw1["xxx_duration"] = sw1["xxx_duration"].fillna(0)
    sw1["min_per_machine"] = sw1["xxx_duration"] / 60 / sw1["machine_count"]
    s1 = (
        sw1[sw1["state"].isin(control_states_indiv)]
        .groupby("week_of_sample")["min_per_machine"].mean().reset_index()
    )
    s1["date"] = s1["week_of_sample"].map(week_dates)
    s1 = s1.sort_values("date").rename(columns={"min_per_machine": "ctrl"})

    # Step 2: weighted by machine count
    ctrl_sw2 = sw1[sw1["state"].isin(control_states_indiv)].copy()
    agg2 = (
        ctrl_sw2.groupby("week_of_sample")
        .apply(lambda g: g["xxx_duration"].sum() / 60 / g["machine_count"].sum())
        .reset_index(name="ctrl")
    )
    agg2["date"] = agg2["week_of_sample"].map(week_dates)
    s2 = agg2.sort_values("date")

    # Step 3: p95 winsorization (nonzero obs)
    nonzero = mw_site.loc[mw_site["total_duration"] > 0, "total_duration"]
    if len(nonzero) == 0:
        s3 = s2.copy()
    else:
        p95_site = nonzero.quantile(0.95)
        mw_site_w = mw_site.copy()
        mw_site_w["total_duration"] = mw_site_w["total_duration"].clip(upper=p95_site)
        sw3 = (
            denom.merge(
                mw_site_w.groupby(["state", "week_of_sample"])["total_duration"]
                .sum().reset_index(name="xxx_duration"),
                on=["state", "week_of_sample"], how="left",
            )
        )
        sw3["xxx_duration"] = sw3["xxx_duration"].fillna(0)
        ctrl_sw3 = sw3[sw3["state"].isin(control_states_indiv)].copy()
        agg3 = (
            ctrl_sw3.groupby("week_of_sample")
            .apply(lambda g: g["xxx_duration"].sum() / 60 / g["machine_count"].sum())
            .reset_index(name="ctrl")
        )
        agg3["date"] = agg3["week_of_sample"].map(week_dates)
        s3 = agg3.sort_values("date")

    # Step 4: within-machine FE demeaning
    machine_means_site = mw_site_w.groupby("machine_id")["total_duration"].mean().rename("machine_mean")
    mw_fe = mw_site_w.join(machine_means_site, on="machine_id")
    mw_fe["duration_demeaned"] = mw_fe["total_duration"] - mw_fe["machine_mean"]
    sw4 = (
        denom.merge(
            mw_fe.groupby(["state", "week_of_sample"])["duration_demeaned"]
            .sum().reset_index(name="xxx_duration_dm"),
            on=["state", "week_of_sample"], how="left",
        )
    )
    sw4["xxx_duration_dm"] = sw4["xxx_duration_dm"].fillna(0)
    ctrl_sw4 = sw4[sw4["state"].isin(control_states_indiv)].copy()
    agg4 = (
        ctrl_sw4.groupby("week_of_sample")
        .apply(lambda g: g["xxx_duration_dm"].sum() / 60 / g["machine_count"].sum())
        .reset_index(name="ctrl_dm")
    )
    agg4["date"] = agg4["week_of_sample"].map(week_dates)
    agg4 = agg4.sort_values("date")
    agg4["ctrl"] = agg4["ctrl_dm"] + s3["ctrl"].mean()
    s4 = agg4[["date", "ctrl"]].copy()

    site_steps[site] = {"s0": s0, "s1": s1, "s2": s2, "s3": s3, "s4": s4}
    print(f"    s0={s0['ctrl'].mean():.3f}  s1={s1['ctrl'].mean():.3f}  "
          f"s3={s3['ctrl'].mean():.3f}  s4={s4['ctrl'].mean():.3f}")

# ============================================================================
# PLOT B: 2×3 grid, one panel per site, all steps overlaid
# ============================================================================

print("\nPlotting by-site figure...")

fig, axes = plt.subplots(2, 3, figsize=(16, 9), sharey=False)

for i, site in enumerate(SITES):
    ax = axes[i // 3, i % 3]
    ss = site_steps[site]
    lines_site = [
        (ss["s0"], "Step 0: State-level aggregates (previous file)",        "--", COLORS5[1]),
        (ss["s1"], "Step 1: Individual, states equally weighted",            "-",  COLORS5[0]),
        (ss["s2"], "Step 2: Weight states by machine count",                 "-",  COLORS5[2]),
        (ss["s3"], "Step 3: Winsorize at p95 of nonzero machine-weeks",      "-",  COLORS5[3]),
        (ss["s4"], "Step 4: Subtract machine time-average, re-center",       "-",  COLORS5[4]),
    ]
    for df, label, ls, color in lines_site:
        ax.plot(df["date"], df["ctrl"], color=color, linewidth=1.2, linestyle=ls, label=label)
    ax.set_title(SITE_LABELS[site], fontsize=11)
    if i % 3 == 0:
        ax.set_ylabel("Min / machine / week")
    if i == 0:
        ax.legend(fontsize=7)
    fmt_date_axis(ax)

fig.suptitle(
    "Control state time series — aggregation steps by site\n(min / machine / week)",
    fontsize=13, y=1.01,
)
plt.tight_layout()

out_path = os.path.join(output_dir, "indiv_timeseries_control_by_site.png")
fig.savefig(out_path, dpi=300, bbox_inches="tight")
print(f"Saved: {out_path}")
plt.close(fig)
