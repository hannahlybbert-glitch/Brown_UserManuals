# Author: Matt Brown, assisted by Claude
# Created: 02/24/2026
# Purpose: Individual-level usage distribution histograms by XXX site

"""
Individual-Level Usage Distribution Histograms

Plots per-machine-week usage distributions (minutes) for each XXX site.
Horizontal reference lines at p90, p95, p99 inform winsorization threshold.
Subtitle shows share of machine-weeks with any nonzero usage.

Analysis sample: machines appearing in machine_demographics.parquet
(includes gender==Unknown; excludes machines with no demographic record).

Usage: python code/descriptives/indiv_descriptives_histogram.py
       (Run on cluster — panel files are large)

Inputs:
- data/Aggregation/machine_panel/machine_demographics.parquet
- data/Aggregation/machine_panel/machine_aggregated_{SITE}.parquet x6

Outputs:
- output/descriptives/Aggregation/matt/histogram_indiv_usage.png
"""

import os
import sys
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

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
    ("PORNHUB.COM",       "Pornhub"),
    ("CHATURBATE.COM",    "Chaturbate"),
    ("XHAMSTER.COM",      "xHamster"),
    ("XNXX.COM",          "XNXX"),
    ("XVIDEOS.COM",       "XVideos"),
    ("other_XXX_sites",   "Other XXX"),
]

# ============================================================================
# LOAD DEMOGRAPHICS — analysis sample
# ============================================================================

print("Loading machine demographics...")
demos = pd.read_parquet(
    os.path.join(data_dir, "machine_demographics.parquet"),
    columns=["machine_id"]
)
demo_ids = set(demos["machine_id"])
n_demo = len(demo_ids)
print(f"  Machines in demographics: {n_demo:,}")

# ============================================================================
# PER-SITE PROCESSING
# ============================================================================

site_data = {}

for file_key, label in SITES:
    fname = os.path.join(data_dir, f"machine_aggregated_{file_key}.parquet")
    print(f"\nProcessing {label} ...")

    panel = pd.read_parquet(fname, columns=["machine_id", "week_of_sample", "total_duration"])

    # Analysis sample filter
    in_demo = panel["machine_id"].isin(demo_ids)
    panel = panel.loc[in_demo].copy()

    n_panel_machines = panel["machine_id"].nunique()
    n_panel_rows = len(panel)
    print(f"  Panel machines (in demo): {n_panel_machines:,}")
    print(f"  Panel machine-weeks:      {n_panel_rows:,}")

    # Nonzero share — denominator excludes null weeks (total_duration is NaN)
    n_nonnull = panel["total_duration"].notna().sum()
    n_nonzero = (panel["total_duration"] > 0).sum()
    share_nonzero = n_nonzero / n_nonnull if n_nonnull > 0 else 0.0
    print(f"  Non-null machine-weeks:   {n_nonnull:,}")
    print(f"  Nonzero machine-weeks:    {n_nonzero:,} ({share_nonzero:.2%})")

    # Distribution: positive observations only, convert seconds -> minutes
    pos = panel.loc[panel["total_duration"] > 0, "total_duration"].copy()
    minutes = pos / 60.0

    mean_min = minutes.mean()
    p90 = minutes.quantile(0.90)
    p95 = minutes.quantile(0.95)
    p99 = minutes.quantile(0.99)
    print(f"  mean={mean_min:.1f} min  p90={p90:.1f} min  p95={p95:.1f} min  p99={p99:.1f} min")

    site_data[file_key] = {
        "label": label,
        "minutes": minutes,
        "share_nonzero": share_nonzero,
        "mean": mean_min,
        "p90": p90,
        "p95": p95,
        "p99": p99,
    }

# ============================================================================
# PLOT
# ============================================================================

fig, axes = plt.subplots(2, 3, figsize=(15, 10), sharey=False)
axes_flat = axes.flatten()

bar_color = COLOR_PALETTE[0]
vline_colors = {"mean": "#009E73", "p90": "#0B3954", "p95": "#9a8873", "p99": "#b4adea"}

for ax, (file_key, _) in zip(axes_flat, SITES):
    d = site_data[file_key]
    minutes = d["minutes"]

    # Log-spaced bins from ~0 to max
    log_min = np.log10(max(minutes.min(), 0.01))
    log_max = np.log10(minutes.max())
    bins = np.logspace(log_min, log_max, 60)

    # Normalize to share of observations (bars sum to 1)
    counts, bin_edges = np.histogram(minutes, bins=bins)
    shares = counts / counts.sum()
    ax.bar(bin_edges[:-1], shares, width=np.diff(bin_edges),
           align="edge", color=bar_color, alpha=0.75, linewidth=0)
    ax.set_xscale("log")

    # Reference lines
    ax.axvline(d["mean"], color=vline_colors["mean"], linestyle="-",
               linewidth=1.4, label=f"mean={d['mean']:.0f}m")
    for pct, val, col in [("p90", d["p90"], vline_colors["p90"]),
                           ("p95", d["p95"], vline_colors["p95"]),
                           ("p99", d["p99"], vline_colors["p99"])]:
        ax.axvline(val, color=col, linestyle="--", linewidth=1.2, label=f"{pct}={val:.0f}m")

    ax.legend(fontsize=8, framealpha=0.85)

    ax.set_xlabel("Minutes per machine-week")
    col_idx = list(ax.get_figure().axes).index(ax) % 3
    ax.set_ylabel("Share of observations" if col_idx == 0 else "")
    ax.set_title(
        f"{d['label']}\n{d['share_nonzero']:.2%} of machine-weeks nonzero",
        fontsize=11
    )
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:g}"))
    ax.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1, decimals=1))

# Hide unused 6th panel slot if needed (we have exactly 6 sites, so none to hide)

fig.suptitle("Machine-week usage distribution (nonzero observations)", y=1.01, fontsize=14)
plt.tight_layout()

out_path = os.path.join(output_dir, "histogram_indiv_usage.png")
fig.savefig(out_path, dpi=300, bbox_inches="tight")
print(f"\nSaved: {out_path}")
plt.close(fig)
