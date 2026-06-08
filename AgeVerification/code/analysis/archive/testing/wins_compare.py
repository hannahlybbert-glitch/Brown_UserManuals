# Author: Hannah Lybbert
# Created: 03/30/2026
# Purpose: Compare raw Pornhub minutes distribution across desktop and mobile machines

"""
Winsorization Comparison — Desktop vs Mobile Pornhub Minutes Distribution

Loads machine_aggregated_PORNHUB.COM.parquet from both the desktop and mobile
machine panels. For each machine, computes mean weekly raw (unwinsorized) Pornhub
minutes across nonzero weeks. Reports key quantiles and plots side-by-side bar charts.

Purpose: examine tail behavior to inform winsorization decisions.

Quantiles reported: 50th, 75th, 90th, 95th, 97th, 99th percentile of the
per-machine mean weekly minutes distribution (baseline weeks 1-52, nonzero machines only).

Output:
  output/analysis/wins_compare/pornhub_quantiles_desktop_vs_mobile_wins.png
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

file_dir     = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(file_dir, "..", ".."))
sys.path.insert(0, os.path.join(project_root, "code"))
from plot_style import apply_plot_style, COLOR_PALETTE

apply_plot_style()

# ============================================================================
# FILE PATHS
# ============================================================================
CATEGORY = "PORNHUB.COM"

desktop_file = os.path.join(
    project_root, "data", "Aggregation", "machine_panel",
    f"machine_aggregated_{CATEGORY}.parquet"
)
mobile_file = os.path.join(
    project_root, "data", "Aggregation", "mobile_machine_panel",
    f"machine_aggregated_{CATEGORY}.parquet"
)
output_dir = os.path.join(project_root, "output", "analysis", "wins_compare")
os.makedirs(output_dir, exist_ok=True)

QUANTILES = [0.50, 0.75, 0.90, 0.95, 0.99]
Q_LABELS  = ["p50", "p75", "p90", "p95", "p99"]

# ============================================================================
# HELPER: load and aggregate to machine level (no winsorization)
# ============================================================================
def load_and_prepare(path, label):
    print(f"\n[{label}] Loading {path}...")
    df = pd.read_parquet(path)
    print(f"  Rows loaded:           {len(df):,}")

    # Filter to baseline weeks 1-52 and nonzero rows, convert seconds to minutes
    nonzero = df[df["week_of_sample"].isin(range(1, 53)) & (df["total_duration"] > 0)].copy()
    nonzero["minutes"] = nonzero["total_duration"] / 60
    print(f"  Nonzero machine-weeks (weeks 1-52): {len(nonzero):,}")

    # Aggregate to machine level: mean weekly raw minutes
    machine_avg = (
        nonzero
        .groupby("machine_id")["minutes"]
        .mean()
        .reset_index(name="mean_min")
    )
    print(f"  Unique machines (nonzero): {len(machine_avg):,}")
    return machine_avg

# ============================================================================
# LOAD DATA
# ============================================================================
desktop_machines = load_and_prepare(desktop_file, "DESKTOP")
mobile_machines  = load_and_prepare(mobile_file,  "MOBILE")

# ============================================================================
# COMPUTE QUANTILES
# ============================================================================
def compute_quantiles(machine_avg):
    return [float(np.quantile(machine_avg["mean_min"], q)) for q in QUANTILES]

desktop_vals = compute_quantiles(desktop_machines)
mobile_vals  = compute_quantiles(mobile_machines)

# ============================================================================
# REPORT TO CONSOLE
# ============================================================================
print("\n" + "=" * 60)
print("PORNHUB — Mean Weekly Raw Minutes per Machine")
print("(baseline weeks 1-52, nonzero machines only, sessions winsorized to 95th percentile)")
print("=" * 60)
print(f"{'Quantile':<10} {'Desktop':>12} {'Mobile':>12}")
print("-" * 36)
for label, dv, mv in zip(Q_LABELS, desktop_vals, mobile_vals):
    print(f"{label:<10} {dv:>11.2f}  {mv:>11.2f}")
print("=" * 60)
print(f"  Desktop machines: {len(desktop_machines):,}")
print(f"  Mobile  machines: {len(mobile_machines):,}")

# ============================================================================
# PLOT
# ============================================================================
fig, ax = plt.subplots(figsize=(10, 5))

x     = np.arange(len(Q_LABELS))
width = 0.35

bars_d = ax.bar(x - width / 2, desktop_vals, width, label=f"Desktop (n={len(desktop_machines):,})",
                color=COLOR_PALETTE[0], edgecolor="white", linewidth=0.5)
bars_m = ax.bar(x + width / 2, mobile_vals,  width, label=f"Mobile  (n={len(mobile_machines):,})",
                color=COLOR_PALETTE[1], edgecolor="white", linewidth=0.5)

all_vals = desktop_vals + mobile_vals
for bars, vals in [(bars_d, desktop_vals), (bars_m, mobile_vals)]:
    for bar, val in zip(bars, vals):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(all_vals) * 0.01,
            f"{val:.1f}",
            ha="center", va="bottom", fontsize=9
        )

ax.set_xticks(x)
ax.set_xticklabels(Q_LABELS)
ax.set_xlabel("Percentile")
ax.set_ylabel("Mean weekly minutes")
ax.set_title(
    "Distribution of Mean Weekly Pornhub Minutes per Machine\n"
    "(baseline weeks 1–52, sessions winsorized to 95th percentile)"
)
ax.legend()
fig.tight_layout()

out_path = os.path.join(output_dir, "pornhub_quantiles_desktop_vs_mobile_wins.png")
fig.savefig(out_path, dpi=150, bbox_inches="tight")
print(f"\nSaved: {out_path}")

# ============================================================================
# HISTOGRAM — avg minutes per machine (nonzero weeks only)
# ============================================================================
fig2, ax2 = plt.subplots(figsize=(10, 5))

combined_max = max(desktop_machines["mean_min"].max(), mobile_machines["mean_min"].max())
bins = np.linspace(0, combined_max, 60)

ax2.hist(desktop_machines["mean_min"], bins=bins, color=COLOR_PALETTE[0], edgecolor="white",
         linewidth=0.3, alpha=0.7, label=f"Desktop (n={len(desktop_machines):,})")
ax2.hist(mobile_machines["mean_min"],  bins=bins, color=COLOR_PALETTE[1], edgecolor="white",
         linewidth=0.3, alpha=0.7, label=f"Mobile  (n={len(mobile_machines):,})")

ax2.set_xlabel("Mean weekly Pornhub minutes (nonzero weeks)")
ax2.set_ylabel("Number of machines")
ax2.set_title(
    "Distribution of Mean Weekly Pornhub Minutes per Machine\n"
    "(baseline weeks 1–52, nonzero weeks only, sessions winsorized to 95th percentile)"
)
ax2.legend()
fig2.tight_layout()

hist_path = os.path.join(output_dir, "pornhub_avg_minutes_histogram_wins.png")
fig2.savefig(hist_path, dpi=150, bbox_inches="tight")
print(f"Saved: {hist_path}")
