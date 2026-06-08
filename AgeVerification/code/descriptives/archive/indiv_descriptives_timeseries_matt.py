# Author: Matt Brown, assisted by Claude
# Created: 02/24/2026
# Purpose: National individual-level time series — raw vs. p95-winsorized mean

"""
Individual-Level Time Series (All Units)

For each XXX site, plots weekly mean minutes per active machine:
  - Raw: mean of total_duration (minutes) across non-null machine-weeks
  - Winsorized: same, after capping at the site-specific p95

Analysis sample: machines in machine_demographics.parquet.
No state filter applied.

Usage: python code/descriptives/indiv_descriptives_timeseries.py
       (Run on cluster — panel files are large)

Inputs:
- data/Aggregation/machine_panel/machine_demographics.parquet
- data/Aggregation/machine_panel/machine_aggregated_{SITE}.parquet x6
- data/Aggregation/final_aggregated.csv  (week_of_sample → date mapping)

Outputs:
- output/descriptives/Aggregation/matt/timeseries_indiv_raw_vs_winsorized.png
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

    # Analysis sample; keep only nonzero usage weeks (active machine-weeks)
    panel = panel.loc[panel["machine_id"].isin(demo_ids)].copy()
    panel = panel.loc[panel["total_duration"] > 0].copy()

    # Convert seconds → minutes
    panel["minutes"] = panel["total_duration"] / 60.0

    # Site-level p95 cap (computed over nonzero observations only)
    p95 = panel["minutes"].quantile(0.95)
    print(f"  p95 cap: {p95:.1f} min")

    panel["minutes_wins"] = panel["minutes"].clip(upper=p95)

    # Weekly means
    ts = (
        panel.groupby("week_of_sample")
        .agg(
            mean_raw=("minutes", "mean"),
            mean_wins=("minutes_wins", "mean"),
            n_active=("minutes", "count"),
        )
        .reset_index()
    )
    ts["date"] = ts["week_of_sample"].map(week_dates)
    ts = ts.sort_values("date")

    print(f"  Weeks with data: {len(ts)}")
    print(f"  Mean raw (overall): {ts['mean_raw'].mean():.2f} min")
    print(f"  Mean wins (overall): {ts['mean_wins'].mean():.2f} min")

    site_ts[file_key] = {"label": label, "ts": ts, "p95": p95}

# ============================================================================
# PLOT
# ============================================================================

color_raw  = COLOR_PALETTE[0]  # maroon
color_wins = COLOR_PALETTE[2]  # blue

fig, axes = plt.subplots(2, 3, figsize=(15, 8), sharey=False)
axes_flat = axes.flatten()

for ax, (file_key, _) in zip(axes_flat, SITES):
    d = site_ts[file_key]
    ts = d["ts"]

    ax.plot(ts["date"], ts["mean_raw"],  color=color_raw,  linewidth=1.4,
            label="Raw")
    ax.plot(ts["date"], ts["mean_wins"], color=color_wins, linewidth=1.4,
            linestyle="--", label=f"Wins. (p95={d['p95']:.0f}m)")

    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.tick_params(axis="x", rotation=0)

    col_idx = list(fig.axes).index(ax) % 3
    ax.set_ylabel("Min / active machine-week\n(nonzero obs only)" if col_idx == 0 else "")
    ax.set_title(d["label"], fontsize=11)
    ax.legend(fontsize=8, framealpha=0.85)

fig.suptitle(
    "Weekly mean usage per active machine — raw vs. p95-winsorized (all units)",
    fontsize=13, y=1.01,
)
plt.tight_layout()

out_path = os.path.join(output_dir, "timeseries_indiv_min_per_nonzero_machweek.png")
fig.savefig(out_path, dpi=300, bbox_inches="tight")
print(f"\nSaved: {out_path}")
plt.close(fig)
