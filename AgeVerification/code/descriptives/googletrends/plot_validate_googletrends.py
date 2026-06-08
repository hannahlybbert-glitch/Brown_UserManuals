#!/usr/bin/env python3
# Author: Emily
# Created: 2026-02-16
# Purpose: Plot Comscore session rates alongside Google Trends index
#          for each major adult site, to validate that the two data sources show similar patterns.
#          Two sets of plots: (1) Google-referred sessions per 1,000 Google sessions vs Google Trends
#                             (2) All sessions per 1,000 total sessions vs Google Trends
#          Plus correlation tables and first-difference regressions.
# Inputs: output/descriptives/validate_googletrends_gtmerge.csv
# Outputs: 15 PNG plots + summary CSVs in output/descriptives/

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy import stats
from pathlib import Path
import os

os.chdir("/Users/emilydavis/Documents/gitrepos/AgeVerification")

INPUT_PATH = Path("output/descriptives/validate_googletrends_gtmerge.csv")
OUTPUT_DIR = Path("output/descriptives")

SITES = ["pornhub", "xvideos", "xnxx", "xhamster", "chaturbate"]


def make_dual_axis_plot(site_df, site, y_col, y_label, filename_suffix):
    """Create a dual-axis plot comparing a Comscore measure to Google Trends."""
    fig, ax1 = plt.subplots(figsize=(10, 5))

    # Left y-axis: Comscore
    color1 = '#1f77b4'
    ax1.plot(site_df['date'], site_df[y_col],
             color=color1, linewidth=1.5, label='Comscore')
    ax1.set_xlabel('Month')
    ax1.set_ylabel(y_label, color=color1)
    ax1.tick_params(axis='y', labelcolor=color1)

    # Right y-axis: Google Trends
    ax2 = ax1.twinx()
    color2 = '#d62728'
    ax2.plot(site_df['date'], site_df['google_trends_index'],
             color=color2, linewidth=1.5, label='Google Trends')
    ax2.set_ylabel('Google Trends Index', color=color2)
    ax2.tick_params(axis='y', labelcolor=color2)

    # X-axis formatting
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b\n%Y'))
    fig.autofmt_xdate(rotation=0, ha='center')

    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

    plt.title(f'{site.capitalize()}: Comscore vs Google Trends')
    plt.tight_layout()

    output_path = OUTPUT_DIR / f"validate_googletrends_{filename_suffix}_{site}.png"
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"Saved: {output_path}")


def compute_correlations(df, y_col, label):
    """Compute correlation between a Comscore measure and Google Trends for each site."""
    corr_results = []
    for site in SITES:
        site_df = df[df['site'] == site].sort_values('month')
        x = site_df['google_trends_index'].values
        y = site_df[y_col].values
        r, p = stats.pearsonr(x, y)
        corr_results.append({
            'site': site,
            'correlation': round(r, 4),
            'p_value': round(p, 6),
            'n': len(site_df),
        })

    corr_df = pd.DataFrame(corr_results)

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


def compute_first_diff_regressions(df, y_col, label):
    """Regress first differences: delta Comscore ~ delta Google Trends for each site."""
    fd_results = []
    for site in SITES:
        site_df = df[df['site'] == site].sort_values('month')
        dy = np.diff(site_df[y_col].values)
        dx = np.diff(site_df['google_trends_index'].values)
        slope, intercept, r_value, p_value, std_err = stats.linregress(dx, dy)
        fd_results.append({
            'site': site,
            'beta': round(slope, 6),
            'intercept': round(intercept, 6),
            'r_squared': round(r_value ** 2, 4),
            'p_value': round(p_value, 6),
            'std_err': round(std_err, 6),
            'n': len(dy),
        })

    fd_df = pd.DataFrame(fd_results)

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
    df = pd.read_csv(INPUT_PATH)

    # Convert month to datetime for plotting
    df['date'] = pd.to_datetime(df['month'].astype(str), format='%Y%m')

    # --- Plot set 1: Google-referred sessions per 1,000 Google sessions ---
    print("=== Google-referred session plots ===")
    for site in SITES:
        site_df = df[df['site'] == site].sort_values('date')
        make_dual_axis_plot(site_df, site,
                            'sessions_per_1000_google',
                            'Sessions per 1,000 Google Sessions',
                            'google')

    # --- Plot set 2: All sessions per 1,000 total sessions ---
    print("\n=== All-sessions plots ===")
    for site in SITES:
        site_df = df[df['site'] == site].sort_values('date')
        make_dual_axis_plot(site_df, site,
                            'sessions_per_1000_all',
                            'Sessions per 1,000 Total Sessions',
                            'allsessions')

    # --- Plot set 3: Google-referred vs Any Session (single y-axis, Comscore only) ---
    print("\n=== Google-referred vs Any Session comparison plots ===")
    for site in SITES:
        site_df = df[df['site'] == site].sort_values('date')

        fig, ax = plt.subplots(figsize=(10, 5))

        ax.plot(site_df['date'], site_df['sessions_per_1000_all'],
                color='#1f77b4', linewidth=1.5, label='Any Session')
        ax.plot(site_df['date'], site_df['sessions_per_1000_google'],
                color='#d62728', linewidth=1.5, label='Google-Referred Session')

        ax.set_xlabel('Month')
        ax.set_ylabel('Sessions per 1,000 Sessions')
        ax.legend(loc='upper left')

        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b\n%Y'))
        fig.autofmt_xdate(rotation=0, ha='center')

        plt.title(f'{site.capitalize()}: Google-Referred vs Any Session')
        plt.tight_layout()

        output_path = OUTPUT_DIR / f"validate_googletrends_comparison_{site}.png"
        plt.savefig(output_path, dpi=150)
        plt.close()
        print(f"Saved: {output_path}")

    print("\nAll plots saved.")

    # --- Correlations ---
    corr_google = compute_correlations(df, 'sessions_per_1000_google',
                                        'Google-referred sessions per 1,000')
    corr_all = compute_correlations(df, 'sessions_per_1000_all',
                                     'All sessions per 1,000')

    # --- First-difference regressions ---
    fd_google = compute_first_diff_regressions(df, 'sessions_per_1000_google',
                                                'Google-referred sessions per 1,000')
    fd_all = compute_first_diff_regressions(df, 'sessions_per_1000_all',
                                             'All sessions per 1,000')

    # Save CSVs
    corr_google.to_csv(OUTPUT_DIR / "validate_googletrends_corr_google.csv", index=False)
    corr_all.to_csv(OUTPUT_DIR / "validate_googletrends_corr_allsessions.csv", index=False)
    fd_google.to_csv(OUTPUT_DIR / "validate_googletrends_firstdiff_google.csv", index=False)
    fd_all.to_csv(OUTPUT_DIR / "validate_googletrends_firstdiff_allsessions.csv", index=False)
    print(f"\nAll tables saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
