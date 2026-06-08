# Author: Matt Brown, assisted by Claude
# Created: 02/24/2026
# Purpose: National individual-level time series — min per active machine-week,
#           raw / p95-winsorized / machine-FE-demeaned

"""
Individual-Level Time Series — Min per Active Machine-Week (All Units)

DV denominator: all non-null machine-weeks (active = observed, includes zeros).
Three series per site:
  1. Raw         — mean(minutes) across non-null machine-weeks
  2. Winsorized  — same after capping at site-level p95 of nonzero obs
  3. FE-demeaned — remove machine mean, re-center to grand mean;
                   isolates within-machine variation, purges composition noise

Analysis sample: machines in machine_demographics.parquet.
No state filter.

Usage: python code/descriptives/indiv_descriptives_timeseries_active.py

Inputs:
- data/Aggregation/machine_panel/machine_demographics.parquet
- data/Aggregation/machine_panel/machine_aggregated_{SITE}.parquet x6
- data/Aggregation/final_aggregated.csv  (week_of_sample → date mapping)

Outputs:
- output/descriptives/Aggregation/matt/timeseries_indiv_min_per_active_machweek.png
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

data_dir = os.path.join(project_root, "data", "Aggregation", "machine_panel")
output_dir = os.path.join(project_root, "output", "descriptives", "Aggregation", "matt")
os.makedirs(output_dir, exist_ok=True)

SITES = [
    ("PORNHUB.COM",      "Pornhub"),
    ("CHATURBATE.COM",   "Chaturbate"),
    ("XHAMSTER.COM",     "xHamster"),
    ("XNXX.COM",         "XNXX"),
    ("XVIDEOS.COM",      "XVideos"),
    ("other_XXX_sites",  "Other XXX"),
]

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
# LOAD DEMOGRAPHICS — analysis sample
# ============================================================================

print("Loading machine demographics...")
demos = pd.read_parquet(
    os.path.join(data_dir, "machine_demographics.parquet"), columns=["machine_id"]
)
demo_ids = set(demos["machine_id"])
print(f"  Machines in demographics: {len(demo_ids):,}")

# ============================================================================
# PER-SITE PROCESSING
# ============================================================================

site_ts = {}

for file_key, label in SITES:
    fname = os.path.join(data_dir, f"machine_aggregated_{file_key}.parquet")
    print(f"\nProcessing {label} ...")

    panel = pd.read_parquet(
        fname, columns=["machine_id", "week_of_sample", "total_duration"]
    )

    # Analysis sample; keep non-null rows (active machine-weeks; zeros included)
    panel = panel.loc[panel["machine_id"].isin(demo_ids)].copy()
    panel = panel.dropna(subset=["total_duration"])

    # Seconds → minutes
    panel["minutes"] = panel["total_duration"] / 60.0

    # p95 cap computed on nonzero observations only
    p95 = panel.loc[panel["minutes"] > 0, "minutes"].quantile(0.95)
    panel["minutes_wins"] = panel["minutes"].clip(upper=p95)
    print(f"  p95 cap: {p95:.1f} min  |  non-null rows: {len(panel):,}")

    # ── Individual-FE demeaning (on winsorized data) ──────────────────────
    # Subtract each machine's mean (computed over its non-null weeks only).
    # Residuals capture within-machine deviations; weekly mean of residuals
    # is the composition-adjusted time series. Force mean-zero by subtracting
    # the unweighted mean of the 157 weekly values (unbalanced panel means
    # the simple weekly average isn't exactly zero without this step).
    machine_means = panel.groupby("machine_id")["minutes_wins"].transform("mean")
    panel["resid_wins"] = panel["minutes_wins"] - machine_means

    # Weekly aggregation
    ts = (
        panel.groupby("week_of_sample")
        .agg(
            mean_raw=("minutes",      "mean"),
            mean_wins=("minutes_wins","mean"),
            mean_fe=("resid_wins",    "mean"),
            n_active=("minutes",      "count"),
        )
        .reset_index()
    )
    # No re-centering — series sits at its natural level near zero,
    # showing within-machine deviations on the same axis as the raw/wins levels.

    ts["date"] = ts["week_of_sample"].map(week_dates)
    ts = ts.sort_values("date")

    print(f"  Weeks: {len(ts)}  |  "
          f"mean raw={ts['mean_raw'].mean():.2f}  "
          f"wins={ts['mean_wins'].mean():.2f}  "
          f"fe mean={ts['mean_fe'].mean():.4f}")

    site_ts[file_key] = {"label": label, "ts": ts, "p95": p95}

# ============================================================================
# PLOT — 2×3 grid, three lines per panel
# ============================================================================

color_raw  = COLOR_PALETTE[0]  # maroon  — raw
color_wins = COLOR_PALETTE[2]  # blue    — winsorized
color_fe   = COLOR_PALETTE[3]  # teal    — TWFE week effects

fig, axes = plt.subplots(2, 3, figsize=(15, 8), sharey=False)
axes_flat = axes.flatten()

for ax, (file_key, _) in zip(axes_flat, SITES):
    d = site_ts[file_key]
    ts = d["ts"]

    ax.plot(ts["date"], ts["mean_raw"],  color=color_raw,  linewidth=1.4,
            label="Raw")
    ax.plot(ts["date"], ts["mean_wins"], color=color_wins, linewidth=1.4,
            linestyle="--", label=f"Wins. (p95={d['p95']:.0f}m)")
    ax.plot(ts["date"], ts["mean_fe"],   color=color_fe,   linewidth=1.4,
            linestyle=":",  label="Indiv-FE demeaned (wins.)")

    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.tick_params(axis="x", rotation=0)

    col_idx = list(fig.axes).index(ax) % 3
    ax.set_ylabel("Min / active machine-week" if col_idx == 0 else "")
    ax.set_title(d["label"], fontsize=11)
    ax.legend(fontsize=8, framealpha=0.85)

fig.suptitle(
    "Weekly mean usage per active machine-week — raw / p95-winsorized / indiv-FE demeaned (wins., mean-zero)",
    fontsize=12, y=1.01,
)
plt.tight_layout()

out_path = os.path.join(output_dir, "timeseries_indiv_min_per_active_machweek.png")
fig.savefig(out_path, dpi=300, bbox_inches="tight")
print(f"\nSaved: {out_path}")
plt.close(fig)
