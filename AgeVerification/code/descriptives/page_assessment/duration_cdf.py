# Author: Hannah Lybbert
# Created: 2026-04-01
# Purpose: CDF plots of Pornhub.com session duration split by pre/post law
#          and pages == 1 vs pages > 1

"""
Reads the pre-built category sessions files (pornhub_sessions.parquet and
mobile_pornhub_sessions.parquet) and produces empirical CDF plots of session
duration for treated states, split by:
  - Period: pre-law (post == 0) vs. post-law (post == 1)
  - Page count: pages == 1 vs. pages > 1

Layout: two side-by-side panels per device type.
  Left panel:  pages == 1
  Right panel: pages > 1
  Each panel:  pre-law (blue) and post-law (red) CDF lines

The x-axis is capped at the 99th percentile of all durations to suppress
outliers; duration is shown in seconds.

Inputs:
  data/ProcessComscore/merged_cat_session_files/pornhub_sessions.parquet
  data/ProcessComscore/merged_cat_session_files/mobile_pornhub_sessions.parquet

Outputs:
  output/descriptives/pages_assessment/desktop/duration_cdf_desktop.png
  output/descriptives/pages_assessment/mobile/duration_cdf_mobile.png

Usage:
  python code/descriptives/page_assessment/duration_cdf.py
  (run from project root)
"""

import os

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

# ==============================================================================
# PATHS
# ==============================================================================
project_root = os.getcwd()

cat_sessions_dir = os.path.join(
    project_root, "data", "ProcessComscore", "merged_cat_session_files"
)

DEVICE_CONFIG = {
    "desktop": {
        "input":  os.path.join(cat_sessions_dir, "pornhub_sessions.parquet"),
        "outdir": os.path.join(project_root, "output", "descriptives",
                               "pages_assessment", "desktop"),
        "outfile": "duration_cdf_desktop.png",
    },
    "mobile": {
        "input":  os.path.join(cat_sessions_dir, "mobile_pornhub_sessions.parquet"),
        "outdir": os.path.join(project_root, "output", "descriptives",
                               "pages_assessment", "mobile"),
        "outfile": "duration_cdf_mobile.png",
    },
}

COLS = ["duration", "pages", "post", "treated"]

# ==============================================================================
# HELPER: COMPUTE EMPIRICAL CDF
# ==============================================================================
def empirical_cdf(series, x_vals):
    """Return CDF values at x_vals for the given series."""
    sorted_vals = np.sort(series.dropna().values)
    n = len(sorted_vals)
    if n == 0:
        return np.full_like(x_vals, np.nan, dtype=float)
    return np.searchsorted(sorted_vals, x_vals, side="right") / n


# ==============================================================================
# MAIN: ONE FIGURE PER DEVICE TYPE
# ==============================================================================
for device, cfg in DEVICE_CONFIG.items():
    print(f"\n{'=' * 60}")
    print(f"{device.upper()}")
    print("=" * 60)

    if not os.path.exists(cfg["input"]):
        print(f"  Input not found: {cfg['input']} — skipping")
        continue

    os.makedirs(cfg["outdir"], exist_ok=True)

    # Load only needed columns; keep treated states only
    df = pd.read_parquet(cfg["input"], columns=COLS)
    df = df[df["treated"] == 1].copy()
    df = df[df["post"].notna()].copy()
    df["post"]       = df["post"].astype(int)
    df["pages_group"] = np.where(df["pages"] == 1, "pages_eq_1", "pages_gt_1")

    n_pre  = (df["post"] == 0).sum()
    n_post = (df["post"] == 1).sum()
    print(f"  Treated-state sessions: {len(df):,}  (pre={n_pre:,}, post={n_post:,})")

    # Winsorize duration at the 95th percentile: values above the cap
    # are replaced with the cap so the CDF reaches 1.0 at that point
    winsor_cap = np.nanpercentile(df["duration"].values, 95)
    df["duration"] = df["duration"].clip(upper=winsor_cap)
    x_vals = np.linspace(0, winsor_cap, 2000)
    print(f"  Duration 95th pct (winsorize cap): {winsor_cap:.0f}s")

    # ------------------------------------------------------------------
    # PLOT
    # ------------------------------------------------------------------
    GROUPS = [
        ("pages_eq_1", "pages == 1"),
        ("pages_gt_1", "pages > 1"),
    ]
    PERIODS = [
        (0, "Pre-law",  "#4878CF"),
        (1, "Post-law", "#D65F5F"),
    ]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)

    for ax, (group_key, group_label) in zip(axes, GROUPS):
        sub_group = df[df["pages_group"] == group_key]

        for post_val, period_label, color in PERIODS:
            sub = sub_group.loc[sub_group["post"] == post_val, "duration"]
            cdf = empirical_cdf(sub, x_vals)
            ax.plot(x_vals, cdf, label=f"{period_label} (n={len(sub):,})",
                    color=color, linewidth=1.8)

        ax.set_title(group_label, fontsize=13)
        ax.set_xlabel("Session duration (seconds)")
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=0))
        ax.legend(fontsize=9)
        ax.set_xlim(0, x_max)
        ax.set_ylim(0, 1)
        ax.grid(axis="y", linestyle="--", alpha=0.4)

    axes[0].set_ylabel("Cumulative share of sessions")

    fig.suptitle(
        f"Pornhub.com ({device.capitalize()}) — session duration CDF\n"
        f"treated states, pre vs. post law",
        fontsize=12,
    )
    fig.tight_layout()

    out_path = os.path.join(cfg["outdir"], cfg["outfile"])
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {out_path}")

print("\nCOMPLETE")
