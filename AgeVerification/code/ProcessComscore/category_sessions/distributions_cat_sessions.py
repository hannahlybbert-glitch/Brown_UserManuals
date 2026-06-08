# Author: Hannah Lybbert
# Created: 2026-04-07
# Purpose: Session-level duration distributions for Pornhub — desktop vs mobile

"""
Pornhub Session Duration Distributions — Desktop vs Mobile

Loads pornhub_sessions.parquet and mobile_pornhub_sessions.parquet.
All sessions in these files are assumed to have duration > 0.
Sessions are filtered to calendar year 2022 (pre-period).

Produces four figures:

  (1) pornhub_session_quantiles.png
      Bar chart: p50/p75/p90/p95/p99 of individual session duration (minutes),
      desktop and mobile side by side. No winsorization.

  (2) pornhub_session_quantiles_wins.png
      Same as (1) but after winsorizing session duration to the 95th percentile
      within each device type separately. Dataset is not saved.

  (3) pornhub_machine_avg_minutes_hist.png
      Overlapping histograms: per-machine mean session duration (minutes),
      desktop and mobile. No winsorization.

  (4) pornhub_machine_avg_minutes_hist_wins.png
      Same as (3) but using winsorized session durations.

Duration column: `duration` (seconds) → converted to minutes throughout.
Winsorization: values above the 95th percentile are capped at the 95th percentile,
computed separately for desktop and mobile.

Usage:
  python code/ProcessComscore/distributions_cat_sessions.py
  (run from project root on the cluster)

Input:
  data/ProcessComscore/merged_cat_session_files/pornhub_sessions.parquet
  data/ProcessComscore/merged_cat_session_files/mobile_pornhub_sessions.parquet

Output:
  output/ProcessComscore/pornhub_sessions/pornhub_session_quantiles.png
  output/ProcessComscore/pornhub_sessions/pornhub_session_quantiles_wins.png
  output/ProcessComscore/pornhub_sessions/pornhub_machine_avg_minutes_hist.png
  output/ProcessComscore/pornhub_sessions/pornhub_machine_avg_minutes_hist_wins.png
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

file_dir     = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(file_dir, "..", "..", ".."))
sys.path.insert(0, os.path.join(project_root, "code"))
from plot_style import apply_plot_style, COLOR_PALETTE

apply_plot_style()

# ==============================================================================
# PATHS
# ==============================================================================
sessions_dir = os.path.join(project_root, "data", "ProcessComscore", "merged_cat_session_files")
desktop_file = os.path.join(sessions_dir, "pornhub_sessions.parquet")
mobile_file  = os.path.join(sessions_dir, "mobile_pornhub_sessions.parquet")

output_dir = os.path.join(project_root, "output", "ProcessComscore", "pornhub_sessions")
os.makedirs(output_dir, exist_ok=True)

QUANTILES       = [0.50, 0.75, 0.90, 0.95, 0.99]
Q_LABELS        = ["p50", "p75", "p90", "p95", "p99"]
QUANTILES_WINS  = [0.50, 0.75, 0.90, 0.95]
Q_LABELS_WINS   = ["p50", "p75", "p90", "p95"]
WINS_PERCENTILE = 0.95

# ==============================================================================
# LOAD DATA
# ==============================================================================
print("=" * 80)
print("PORNHUB SESSION DURATION DISTRIBUTIONS")
print("=" * 80)

PRE_PERIOD_START = pd.Timestamp("2022-01-01")
PRE_PERIOD_END   = pd.Timestamp("2022-12-31")

print(f"\n[DESKTOP] Loading {desktop_file}...")
desktop = pd.read_parquet(desktop_file, columns=["machine_id", "duration", "date"])
print(f"  Rows loaded: {len(desktop):,}")
desktop = desktop[(desktop["date"] >= PRE_PERIOD_START) & (desktop["date"] <= PRE_PERIOD_END)]
print(f"  Rows after filtering to 2022: {len(desktop):,}")

print(f"\n[MOBILE] Loading {mobile_file}...")
mobile = pd.read_parquet(mobile_file, columns=["machine_id", "duration", "date"])
print(f"  Rows loaded: {len(mobile):,}")
mobile = mobile[(mobile["date"] >= PRE_PERIOD_START) & (mobile["date"] <= PRE_PERIOD_END)]
print(f"  Rows after filtering to 2022: {len(mobile):,}")

# Convert seconds to minutes
desktop["minutes"] = desktop["duration"] / 60
mobile["minutes"]  = mobile["duration"]  / 60

n_desktop = len(desktop)
n_mobile  = len(mobile)

# ==============================================================================
# WINSORIZE (cap at 95th percentile within each device type)
# ==============================================================================
desktop_cap = desktop["minutes"].quantile(WINS_PERCENTILE)
mobile_cap  = mobile["minutes"].quantile(WINS_PERCENTILE)

print(f"\n[WINSORIZATION] Capping at 95th percentile:")
print(f"  Desktop cap: {desktop_cap:.2f} min")
print(f"  Mobile  cap: {mobile_cap:.2f} min")

desktop["minutes_wins"] = desktop["minutes"].clip(upper=desktop_cap)
mobile["minutes_wins"]  = mobile["minutes"].clip(upper=mobile_cap)

# ==============================================================================
# COMPUTE SESSION-LEVEL QUANTILES
# ==============================================================================
def session_quantiles(series, qs):
    return [float(series.quantile(q)) for q in qs]

desktop_q      = session_quantiles(desktop["minutes"],      QUANTILES)
mobile_q       = session_quantiles(mobile["minutes"],       QUANTILES)
desktop_q_wins = session_quantiles(desktop["minutes_wins"], QUANTILES_WINS)
mobile_q_wins  = session_quantiles(mobile["minutes_wins"],  QUANTILES_WINS)

# ==============================================================================
# REPORT TO CONSOLE
# ==============================================================================
print("\n" + "=" * 60)
print("PORNHUB — Session Duration Quantiles (minutes)")
print("=" * 60)
print(f"\n  Raw (2022, no winsorization):")
print(f"  {'Quantile':<10} {'Desktop':>12} {'Mobile':>12}")
print("  " + "-" * 36)
for lbl, dv, mv in zip(Q_LABELS, desktop_q, mobile_q):
    print(f"  {lbl:<10} {dv:>11.2f}  {mv:>11.2f}")

print(f"\n  Winsorized to 95th percentile:")
print(f"  {'Quantile':<10} {'Desktop':>12} {'Mobile':>12}")
print("  " + "-" * 36)
for lbl, dv, mv in zip(Q_LABELS_WINS, desktop_q_wins, mobile_q_wins):
    print(f"  {lbl:<10} {dv:>11.2f}  {mv:>11.2f}")

print(f"\n  Desktop sessions: {n_desktop:,}")
print(f"  Mobile  sessions: {n_mobile:,}")

# ==============================================================================
# COMPUTE PER-MACHINE MEAN SESSION MINUTES
# ==============================================================================
desktop_machine_avg      = desktop.groupby("machine_id")["minutes"].mean()
mobile_machine_avg       = mobile.groupby("machine_id")["minutes"].mean()
desktop_machine_avg_wins = desktop.groupby("machine_id")["minutes_wins"].mean()
mobile_machine_avg_wins  = mobile.groupby("machine_id")["minutes_wins"].mean()

print(f"\n  Unique desktop machines: {len(desktop_machine_avg):,}")
print(f"  Unique mobile  machines: {len(mobile_machine_avg):,}")

# ==============================================================================
# HELPER: BAR CHART OF QUANTILES
# ==============================================================================
def plot_quantile_bars(d_vals, m_vals, title, out_path, q_labels=Q_LABELS):
    fig, ax = plt.subplots(figsize=(10, 5))
    x     = np.arange(len(q_labels))
    width = 0.35

    bars_d = ax.bar(x - width / 2, d_vals, width,
                    label=f"Desktop (n={n_desktop:,})",
                    color=COLOR_PALETTE[0], edgecolor="white", linewidth=0.5)
    bars_m = ax.bar(x + width / 2, m_vals, width,
                    label=f"Mobile  (n={n_mobile:,})",
                    color=COLOR_PALETTE[1], edgecolor="white", linewidth=0.5)

    all_vals = d_vals + m_vals
    for bars, vals in [(bars_d, d_vals), (bars_m, m_vals)]:
        for bar, val in zip(bars, vals):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(all_vals) * 0.01,
                f"{val:.1f}",
                ha="center", va="bottom", fontsize=9
            )

    ax.set_xticks(x)
    ax.set_xticklabels(q_labels)
    ax.set_xlabel("Percentile")
    ax.set_ylabel("Session duration (minutes)")
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_path}")

# ==============================================================================
# HELPER: OVERLAPPING HISTOGRAMS OF PER-MACHINE MEAN MINUTES
# ==============================================================================
def plot_machine_avg_hist(d_avg, m_avg, title, out_path):
    fig, ax = plt.subplots(figsize=(10, 5))

    combined_max = max(d_avg.max(), m_avg.max())
    bins = np.linspace(0, combined_max, 60)

    ax.hist(d_avg, bins=bins, color=COLOR_PALETTE[0], edgecolor="white",
            linewidth=0.3, alpha=0.7, label=f"Desktop (n={len(d_avg):,} machines)")
    ax.hist(m_avg, bins=bins, color=COLOR_PALETTE[1], edgecolor="white",
            linewidth=0.3, alpha=0.7, label=f"Mobile  (n={len(m_avg):,} machines)")

    ax.set_xlabel("Mean Pornhub session duration per machine (minutes)")
    ax.set_ylabel("Number of machines")
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_path}")

# ==============================================================================
# PRODUCE FIGURES
# ==============================================================================
print("\n" + "=" * 80)
print("SAVING FIGURES")
print("=" * 80 + "\n")

# Figure 1: session quantiles, no winsorization
plot_quantile_bars(
    desktop_q, mobile_q,
    title=(
        "Pornhub Session Duration by Percentile — Desktop vs Mobile\n"
        "(2022 sessions, no winsorization)"
    ),
    out_path=os.path.join(output_dir, "pornhub_session_quantiles.png"),
)

# Figure 2: session quantiles, winsorized
plot_quantile_bars(
    desktop_q_wins, mobile_q_wins, q_labels=Q_LABELS_WINS,
    title=(
        "Pornhub Session Duration by Percentile — Desktop vs Mobile\n"
        "(2022 sessions, winsorized to 95th percentile)"
    ),
    out_path=os.path.join(output_dir, "pornhub_session_quantiles_wins.png"),
)

# Figure 3: per-machine mean session minutes histogram, no winsorization
plot_machine_avg_hist(
    desktop_machine_avg, mobile_machine_avg,
    title=(
        "Distribution of Mean Pornhub Session Duration per Machine\n"
        "(2022, no winsorization)"
    ),
    out_path=os.path.join(output_dir, "pornhub_machine_avg_minutes_hist.png"),
)

# Figure 4: per-machine mean session minutes histogram, winsorized
plot_machine_avg_hist(
    desktop_machine_avg_wins, mobile_machine_avg_wins,
    title=(
        "Distribution of Mean Pornhub Session Duration per Machine\n"
        "(2022, sessions winsorized to 95th percentile)"
    ),
    out_path=os.path.join(output_dir, "pornhub_machine_avg_minutes_hist_wins.png"),
)

print("\n" + "=" * 80)
print("COMPLETE")
print("=" * 80)
