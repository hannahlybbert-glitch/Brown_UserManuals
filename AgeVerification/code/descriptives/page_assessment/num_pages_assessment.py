# Author:
# Created: 2026-03-31
# Purpose: Assess pages variable and session duration for Pornhub.com, pre vs. post law

"""
For Pornhub.com sessions from treated states only, compare pre- and post-law periods.
Runs separately for desktop and mobile.

  (1) Pages analysis
      - Share of sessions with pages == 1, pre vs. post
      - Histogram: count and share of sessions at each pages value, pre vs. post
      - Monthly trend in pages==1 share
      - Event-study plot: pages==1 share aligned at each state's t=0

  (2) Session duration quantiles conditional on page count
      - Key quantiles of duration for pages == 1 vs. pages > 1, pre vs. post

Pre/post classification uses each state's day_effective from statelaws_dates.csv,
compared to the exact session date derived from time_id (days since 2000-01-01).
Only states with a non-empty day_effective are included (treated states only).
A state can appear in both pre and post bins — even within a single month file —
if its treatment date falls mid-month.

Inputs:
  data/ProcessComscore/merged_session_files/merged_sessions_{YYYYMM}.parquet
  data/ProcessComscore/merged_session_files/merged_mobile_sessions_{YYYYMM}.parquet
  raw/statelaws/statelaws_dates.csv

Outputs saved to device-specific subdirectories:
  output/descriptives/pages_assessment/desktop/pages_histogram_pre_post.csv
  output/descriptives/pages_assessment/desktop/pages_histogram_pre_post.png
  output/descriptives/pages_assessment/desktop/pages_share_monthly.csv
  output/descriptives/pages_assessment/desktop/pages_share_monthly_trend.png
  output/descriptives/pages_assessment/desktop/pages_share_event_study.png
  output/descriptives/pages_assessment/desktop/duration_quantiles_pre_post.csv
  output/descriptives/pages_assessment/desktop/duration_quantiles_pre_post.png
  output/descriptives/pages_assessment/mobile/  (same files, suffixed _mobile)

Usage:
  python code/descriptives/num_pages_assessment.py
  (run from project root on the cluster)
"""

import glob
import os

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

# ==============================================================================
# PATHS AND CONSTANTS
# ==============================================================================
project_root = os.getcwd()

sessions_dir = os.path.join(project_root, "data", "ProcessComscore", "merged_session_files")
laws_path    = os.path.join(project_root, "raw", "statelaws", "statelaws_dates.csv")
output_dir   = os.path.join(project_root, "output", "descriptives", "pages_assessment")
os.makedirs(output_dir, exist_ok=True)

COLS           = ["pages", "duration", "state", "top_web_name", "time_id"]
QUANTILES      = [0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99]
HIST_MAX_PAGES = 15
ES_WINDOW      = 12   # months before/after treatment in event study
BASE_DATE      = pd.Timestamp("2000-01-01")

# File glob patterns and filename stems per device type
DEVICE_CONFIG = {
    "desktop": {
        "glob":   "merged_sessions_??????.parquet",
        "prefix": "merged_sessions_",
    },
    "mobile": {
        "glob":   "merged_mobile_sessions_??????.parquet",
        "prefix": "merged_mobile_sessions_",
    },
}

# ==============================================================================
# LOAD TREATMENT DATES  (shared across both device types)
# ==============================================================================
print("=" * 70)
print("LOADING TREATMENT DATES")
print("=" * 70)

laws = pd.read_csv(laws_path)
laws = laws[laws["day_effective"].notna() & (laws["day_effective"].str.strip() != "")]
laws["treat_date"] = pd.to_datetime(laws["day_effective"].str.strip(), format="%d%b%Y")

treat_dates    = dict(zip(laws["state"], laws["treat_date"]))
treated_states = set(treat_dates.keys())

print(f"  Treated states ({len(treated_states)}): {sorted(treated_states)}")
for st, dt in sorted(treat_dates.items(), key=lambda x: x[1]):
    print(f"    {st}: {dt.date()}")


# ==============================================================================
# HELPER: LOAD AND FILTER SESSIONS FOR ONE DEVICE TYPE
# ==============================================================================
def load_sessions(device):
    cfg    = DEVICE_CONFIG[device]
    fpaths = sorted(glob.glob(os.path.join(sessions_dir, cfg["glob"])))
    print(f"\nFound {len(fpaths)} {device} session files")

    chunks = []
    for fpath in fpaths:
        yyyymm = os.path.basename(fpath).replace(cfg["prefix"], "").replace(".parquet", "")

        try:
            table = pq.read_table(
                fpath,
                columns=COLS,
                filters=[("state", "in", list(treated_states))],
            )
            df = table.to_pandas()
        except Exception:
            df = pd.read_parquet(fpath, columns=COLS)
            df = df[df["state"].isin(treated_states)]

        df = df[df["top_web_name"].str.upper() == "PORNHUB.COM"]

        if len(df) == 0:
            print(f"  {yyyymm}: 0 Pornhub rows in treated states — skipping")
            continue

        df["session_date"] = BASE_DATE + pd.to_timedelta(df["time_id"], unit="D")
        df["treat_date"]   = df["state"].map(treat_dates)
        df["period"]       = np.where(df["session_date"] >= df["treat_date"], "post", "pre")
        df["yyyymm"]       = yyyymm

        df = df.drop(columns=["session_date", "treat_date", "top_web_name", "time_id"])
        chunks.append(df)

        n_pre  = (df["period"] == "pre").sum()
        n_post = (df["period"] == "post").sum()
        print(f"  {yyyymm}: {len(df):,} rows  (pre={n_pre:,}, post={n_post:,})")

    data = pd.concat(chunks, ignore_index=True)
    n_pre  = (data["period"] == "pre").sum()
    n_post = (data["period"] == "post").sum()
    print(f"Total {device} Pornhub sessions from treated states: {len(data):,}")
    print(f"  Pre-law:  {n_pre:,}  ({n_pre  / len(data) * 100:.1f}%)")
    print(f"  Post-law: {n_post:,}  ({n_post / len(data) * 100:.1f}%)")
    return data


# ==============================================================================
# HELPER: RUN ALL ANALYSES FOR ONE DEVICE TYPE
# ==============================================================================
def run_analysis(data, device):
    label  = device.capitalize()
    subdir = os.path.join(output_dir, device)
    os.makedirs(subdir, exist_ok=True)
    suffix = f"_{device}" if device == "mobile" else ""
    out    = lambda fname: os.path.join(subdir, f"{fname}{suffix}")

    # --------------------------------------------------------------------------
    # ANALYSIS 1: PAGES DISTRIBUTION AND PAGES==1 SHARE
    # --------------------------------------------------------------------------
    print(f"\n{'=' * 70}")
    print(f"[{label}] ANALYSIS 1: Pages distribution and pages==1 share")
    print("=" * 70)

    # Histogram CSV
    hist_rows = []
    for period in ["pre", "post"]:
        sub   = data.loc[data["period"] == period, "pages"]
        total = len(sub)
        vc    = sub.value_counts(normalize=False).sort_index()
        for pages_val, count in vc.items():
            hist_rows.append({"pages": pages_val, "period": period,
                               "count": count, "share": count / total})

    hist_df = pd.DataFrame(hist_rows)
    hist_df.to_csv(out("pages_histogram_pre_post") + ".csv", index=False)
    print(f"  Saved: {out('pages_histogram_pre_post')}.csv")

    # Quick-look pivot
    pivot = (
        hist_df[hist_df["pages"] <= 10]
        .pivot(index="pages", columns="period", values="share")
        .rename(columns={"pre": "share_pre", "post": "share_post"})
    )
    pivot["diff_post_minus_pre"] = pivot["share_post"] - pivot["share_pre"]
    print("\n  Share of sessions at each pages value (1–10):")
    print(pivot.to_string(float_format="{:.4f}".format))

    p1_pre  = hist_df.loc[(hist_df["pages"] == 1) & (hist_df["period"] == "pre"),  "share"].values[0]
    p1_post = hist_df.loc[(hist_df["pages"] == 1) & (hist_df["period"] == "post"), "share"].values[0]
    print(f"\n  pages==1 share:  pre={p1_pre:.4f}  post={p1_post:.4f}  diff={p1_post - p1_pre:+.4f}")

    # Plot 1: Side-by-side bar chart
    plot_df    = hist_df[hist_df["pages"] <= HIST_MAX_PAGES].copy()
    pages_vals = sorted(plot_df["pages"].unique())
    x, width   = np.arange(len(pages_vals)), 0.35

    def _share(p, period):
        mask = (plot_df["pages"] == p) & (plot_df["period"] == period)
        return plot_df.loc[mask, "share"].values[0] if mask.any() else 0

    pre_shares  = [_share(p, "pre")  for p in pages_vals]
    post_shares = [_share(p, "post") for p in pages_vals]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - width / 2, pre_shares,  width, label="Pre-law",  color="#4878CF", alpha=0.85)
    ax.bar(x + width / 2, post_shares, width, label="Post-law", color="#D65F5F", alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels([str(p) for p in pages_vals])
    ax.set_xlabel("Pages per session")
    ax.set_ylabel("Share of sessions")
    ax.set_title(f"Pornhub.com ({label}) — distribution of pages per session\n"
                 f"(treated states, pre vs. post law)")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=1))
    ax.legend()
    ax.annotate(
        f"pages==1 share: pre={p1_pre:.3f}  post={p1_post:.3f}  diff={p1_post - p1_pre:+.3f}",
        xy=(0.5, 0.97), xycoords="axes fraction", ha="center", va="top", fontsize=9,
        bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.7),
    )
    fig.tight_layout()
    fig.savefig(out("pages_histogram_pre_post") + ".png", dpi=150)
    plt.close(fig)
    print(f"  Saved: {out('pages_histogram_pre_post')}.png")

    # Monthly trend CSV
    monthly = (
        data.groupby(["yyyymm", "state", "period"])
        .apply(lambda g: pd.Series({
            "n_sessions":       len(g),
            "n_pages_eq_1":     (g["pages"] == 1).sum(),
            "share_pages_eq_1": (g["pages"] == 1).mean(),
        }))
        .reset_index()
    )
    monthly.to_csv(out("pages_share_monthly") + ".csv", index=False)
    print(f"  Saved: {out('pages_share_monthly')}.csv")

    monthly_pooled = (
        data.groupby("yyyymm")
        .apply(lambda g: pd.Series({
            "n_sessions":       len(g),
            "share_pages_eq_1": (g["pages"] == 1).mean(),
            "pct_post":         (g["period"] == "post").mean(),
        }))
        .reset_index()
    )
    print("\n  Monthly pages==1 share (pooled across treated states):")
    print(monthly_pooled.to_string(index=False, float_format="{:.4f}".format))

    # Plot 2: Monthly trend
    monthly_pooled["date"] = pd.to_datetime(monthly_pooled["yyyymm"], format="%Y%m")
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(monthly_pooled["date"], monthly_pooled["share_pages_eq_1"],
            marker="o", linewidth=1.5, color="#333333", label="pages==1 share")
    treated_months = monthly_pooled[monthly_pooled["pct_post"] > 0]
    if not treated_months.empty:
        first_any_treat = treated_months["date"].min()
        ax.axvline(first_any_treat, color="#D65F5F", linestyle="--", linewidth=1,
                   label=f"First treatment ({first_any_treat.strftime('%b %Y')})")
    ax.set_xlabel("Month")
    ax.set_ylabel("Share of sessions with pages == 1")
    ax.set_title(f"Pornhub.com ({label}) — monthly pages==1 share\n"
                 f"(treated states pooled, pre vs. post law)")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=1))
    ax.legend()
    fig.tight_layout()
    fig.savefig(out("pages_share_monthly_trend") + ".png", dpi=150)
    plt.close(fig)
    print(f"  Saved: {out('pages_share_monthly_trend')}.png")

    # Plot 3: Event study
    monthly["date"]       = pd.to_datetime(monthly["yyyymm"], format="%Y%m")
    monthly["treat_date"] = monthly["state"].map(treat_dates).dt.to_period("M").dt.to_timestamp()
    monthly["t"] = (
        (monthly["date"].dt.year  - monthly["treat_date"].dt.year) * 12
        + (monthly["date"].dt.month - monthly["treat_date"].dt.month)
    )
    es = (
        monthly.groupby("t")
        .apply(lambda g: np.average(g["share_pages_eq_1"], weights=g["n_sessions"]))
        .reset_index(name="share_pages_eq_1")
    )
    es = es[es["t"].between(-ES_WINDOW, ES_WINDOW)]

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(es["t"], es["share_pages_eq_1"], marker="o", linewidth=1.5, color="#333333")
    ax.axvline(0, color="#D65F5F", linestyle="--", linewidth=1.2, label="Treatment (t = 0)")
    ax.axvspan(0, ES_WINDOW, alpha=0.06, color="#D65F5F")
    ax.set_xlabel("Months relative to treatment")
    ax.set_ylabel("Share of sessions with pages == 1")
    ax.set_title(f"Pornhub.com ({label}) — pages==1 share around law enactment\n"
                 f"(event study, states stacked at t = 0, session-weighted)")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=1))
    ax.xaxis.set_major_locator(mticker.MultipleLocator(3))
    ax.legend()
    fig.tight_layout()
    fig.savefig(out("pages_share_event_study") + ".png", dpi=150)
    plt.close(fig)
    print(f"  Saved: {out('pages_share_event_study')}.png")

    # --------------------------------------------------------------------------
    # ANALYSIS 2: DURATION QUANTILES BY PAGES GROUP AND PERIOD
    # --------------------------------------------------------------------------
    print(f"\n{'=' * 70}")
    print(f"[{label}] ANALYSIS 2: Duration quantiles by pages group (==1 vs >1) and period")
    print("=" * 70)

    data["pages_group"] = np.where(data["pages"] == 1, "pages_eq_1", "pages_gt_1")

    dur_rows = []
    for period in ["pre", "post"]:
        for pg in ["pages_eq_1", "pages_gt_1"]:
            sub = data.loc[
                (data["period"] == period) & (data["pages_group"] == pg), "duration"
            ]
            row = {"period": period, "pages_group": pg,
                   "n_sessions": len(sub), "mean_dur": sub.mean()}
            for q in QUANTILES:
                row[f"p{int(q * 100)}"] = sub.quantile(q)
            dur_rows.append(row)

    dur_df = pd.DataFrame(dur_rows)
    print(dur_df.to_string(index=False))
    dur_df.to_csv(out("duration_quantiles_pre_post") + ".csv", index=False)
    print(f"\n  Saved: {out('duration_quantiles_pre_post')}.csv")


# ==============================================================================
# MAIN: RUN FOR DESKTOP THEN MOBILE
# ==============================================================================
for device in ["desktop", "mobile"]:
    print(f"\n{'#' * 70}")
    print(f"# {device.upper()}")
    print(f"{'#' * 70}")

    data = load_sessions(device)
    run_analysis(data, device)

print("\n" + "=" * 70)
print("COMPLETE")
print("=" * 70)
