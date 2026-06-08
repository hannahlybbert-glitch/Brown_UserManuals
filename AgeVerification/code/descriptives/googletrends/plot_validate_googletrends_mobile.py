#!/usr/bin/env python3
# Author: Emily
# Created: 2026-02-20
# Purpose: Mobile analog of plot_validate_googletrends.py. Merges mobile Comscore session data
#          with Google Trends index and produces:
#          (1) All sessions per 1,000 total mobile sessions vs Google Trends (dual-axis, per site)
#          (2) Minutes per 1,000 total mobile minutes vs Google Trends (dual-axis, per site)
#          (3) Correlation tables and first-difference regressions for both measures
# Note: Google-referred session plots are excluded (not available in mobile data).
# Inputs: output/descriptives/Google Trends/validate_googletrends_mobile.csv
#         raw/googletrends/*.csv (one file per site)
# Outputs: 10 PNG plots + summary CSVs in output/descriptives/Google Trends/

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy import stats
from pathlib import Path
import os

os.chdir("/Users/emilydavis/Documents/gitrepos/AgeVerification")

MOBILE_INPUT  = Path("output/descriptives/Google Trends/validate_googletrends_mobile.csv")
GT_DIR        = Path("raw/googletrends")
OUTPUT_DIR    = Path("output/descriptives/Google Trends")

SITES = ["pornhub", "xvideos", "xnxx", "xhamster", "chaturbate"]

# Map site name -> Google Trends CSV filename
GT_FILES = {
    "pornhub":    "time_series_US_20220101-0000_20260216-1017.csv",
    "xvideos":    "time_series_US_20220101-0000_20260216-1017-2.csv",
    "xnxx":       "time_series_US_20220101-0000_20260216-1017-3.csv",
    "xhamster":   "time_series_US_20220101-0000_20260216-1017-4.csv",
    "chaturbate": "time_series_US_20220101-0000_20260216-1018.csv",
}


def load_google_trends() -> pd.DataFrame:
    """Load all per-site Google Trends CSVs and return a long-format DataFrame
    with columns: site, month (YYYYMM int), google_trends_index."""
    frames = []
    for site, fname in GT_FILES.items():
        gt = pd.read_csv(GT_DIR / fname)
        gt.columns = ['date', 'google_trends_index']
        gt['date'] = pd.to_datetime(gt['date'])
        gt['month'] = gt['date'].dt.year * 100 + gt['date'].dt.month
        gt['site'] = site
        frames.append(gt[['site', 'month', 'google_trends_index']])
    return pd.concat(frames, ignore_index=True)


def load_and_merge() -> pd.DataFrame:
    """Load mobile Comscore data, merge with Google Trends, return merged DataFrame."""
    mobile = pd.read_csv(MOBILE_INPUT)
    gt = load_google_trends()

    df = mobile.merge(gt, on=['site', 'month'], how='inner')
    df['date'] = pd.to_datetime(df['month'].astype(str), format='%Y%m')
    df = df.sort_values(['site', 'month']).reset_index(drop=True)

    print(f"Merged data: {len(df)} rows across {df['site'].nunique()} sites "
          f"and {df['month'].nunique()} months.")
    return df


def make_dual_axis_plot(site_df, site, y_col, y_label, filename_suffix):
    """Dual-axis plot: left = Comscore measure, right = Google Trends."""
    fig, ax1 = plt.subplots(figsize=(10, 5))

    color1 = '#1f77b4'
    ax1.plot(site_df['date'], site_df[y_col],
             color=color1, linewidth=1.5, label='Comscore (mobile)')
    ax1.set_xlabel('Month')
    ax1.set_ylabel(y_label, color=color1)
    ax1.tick_params(axis='y', labelcolor=color1)

    ax2 = ax1.twinx()
    color2 = '#d62728'
    ax2.plot(site_df['date'], site_df['google_trends_index'],
             color=color2, linewidth=1.5, label='Google Trends')
    ax2.set_ylabel('Google Trends Index', color=color2)
    ax2.tick_params(axis='y', labelcolor=color2)

    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b\n%Y'))
    fig.autofmt_xdate(rotation=0, ha='center')

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

    plt.title(f'{site.capitalize()}: Comscore (mobile) vs Google Trends')
    plt.tight_layout()

    output_path = OUTPUT_DIR / f"validate_googletrends_mobile_{filename_suffix}_{site}.png"
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"  Saved: {output_path}")


def compute_correlations(df, y_col, label) -> pd.DataFrame:
    """Pearson correlation between a Comscore measure and Google Trends per site."""
    results = []
    for site in SITES:
        site_df = df[df['site'] == site].sort_values('month')
        x = site_df['google_trends_index'].values
        y = site_df[y_col].values
        r, p = stats.pearsonr(x, y)
        results.append({
            'site': site,
            'correlation': round(r, 4),
            'p_value': round(p, 6),
            'n': len(site_df),
        })

    corr_df = pd.DataFrame(results)

    print(f"\n{'=' * 60}")
    print(f"CORRELATION: {label} vs Google Trends Index")
    print("=" * 60)
    print(corr_df.to_string(index=False))

    print(f"\nMarkdown table ({label}):\n")
    print("| Site | Correlation | p-value | N |")
    print("|------|-------------|---------|---|")
    for _, row in corr_df.iterrows():
        print(f"| {row['site']} | {row['correlation']} | {row['p_value']} | {row['n']} |")

    return corr_df


def compute_first_diff_regressions(df, y_col, label) -> pd.DataFrame:
    """First-difference regression: delta Comscore ~ delta Google Trends per site."""
    results = []
    for site in SITES:
        site_df = df[df['site'] == site].sort_values('month')
        dy = np.diff(site_df[y_col].values)
        dx = np.diff(site_df['google_trends_index'].values)
        slope, intercept, r_value, p_value, std_err = stats.linregress(dx, dy)
        results.append({
            'site': site,
            'beta': round(slope, 6),
            'intercept': round(intercept, 6),
            'r_squared': round(r_value ** 2, 4),
            'p_value': round(p_value, 6),
            'std_err': round(std_err, 6),
            'n': len(dy),
        })

    fd_df = pd.DataFrame(results)

    print(f"\n{'=' * 60}")
    print(f"FIRST-DIFFERENCE REGRESSION: delta {label} ~ delta Google Trends")
    print("=" * 60)
    print(fd_df.to_string(index=False))

    print(f"\nMarkdown table (first differences, {label}):\n")
    print("| Site | Beta | Intercept | R-squared | p-value | Std Error | N |")
    print("|------|------|-----------|-----------|---------|-----------|---|")
    for _, row in fd_df.iterrows():
        print(f"| {row['site']} | {row['beta']} | {row['intercept']} | {row['r_squared']} | {row['p_value']} | {row['std_err']} | {row['n']} |")

    return fd_df


def main():
    print("=" * 60)
    print("PLOT VALIDATE GOOGLE TRENDS - MOBILE")
    print("=" * 60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = load_and_merge()

    # Save merged dataset for reference
    gtmerge_path = OUTPUT_DIR / "validate_googletrends_mobile_gtmerge.csv"
    df.drop(columns='date').to_csv(gtmerge_path, index=False)
    print(f"Merged data saved to: {gtmerge_path}")

    # --- Plot set 1: All sessions per 1,000 total mobile sessions vs Google Trends ---
    print("\n=== All-sessions plots (mobile) ===")
    for site in SITES:
        site_df = df[df['site'] == site].sort_values('date')
        make_dual_axis_plot(site_df, site,
                            'sessions_per_1000_all',
                            'Sessions per 1,000 Total Mobile Sessions',
                            'allsessions')

    # --- Plot set 2: Minutes per 1,000 total mobile minutes vs Google Trends ---
    print("\n=== Minutes-per-1000 plots (mobile) ===")
    for site in SITES:
        site_df = df[df['site'] == site].sort_values('date')
        make_dual_axis_plot(site_df, site,
                            'minutes_per_1000_all',
                            'Minutes per 1,000 Total Mobile Minutes',
                            'minutes')

    print("\nAll plots saved.")

    # --- Correlations ---
    corr_sessions = compute_correlations(df, 'sessions_per_1000_all',
                                         'All mobile sessions per 1,000')
    corr_minutes  = compute_correlations(df, 'minutes_per_1000_all',
                                         'Mobile minutes per 1,000')

    # --- First-difference regressions ---
    fd_sessions = compute_first_diff_regressions(df, 'sessions_per_1000_all',
                                                  'All mobile sessions per 1,000')
    fd_minutes  = compute_first_diff_regressions(df, 'minutes_per_1000_all',
                                                  'Mobile minutes per 1,000')

    # Save summary CSVs
    corr_sessions.to_csv(OUTPUT_DIR / "validate_googletrends_mobile_corr_allsessions.csv", index=False)
    corr_minutes.to_csv(OUTPUT_DIR  / "validate_googletrends_mobile_corr_minutes.csv",     index=False)
    fd_sessions.to_csv(OUTPUT_DIR   / "validate_googletrends_mobile_firstdiff_allsessions.csv", index=False)
    fd_minutes.to_csv(OUTPUT_DIR    / "validate_googletrends_mobile_firstdiff_minutes.csv",     index=False)

    print(f"\nAll tables saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
