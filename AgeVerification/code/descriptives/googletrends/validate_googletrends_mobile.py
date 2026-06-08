#!/usr/bin/env python3
# Author: Emily
# Created: 2026-02-20
# Purpose: Mobile analog of validate_googletrends.py. For each month (Jan 2022 - Dec 2024), compute:
#          1. All sessions to each major adult site per 1,000 total sessions
#          2. Minutes on each site per 1,000 total minutes
# Note: Mobile merged session files do not contain ref_pattern_id, so Google-referred
#       session metrics are not available for mobile data.
# Inputs: merged mobile session parquet files
# Outputs: CSV with columns: month, site, all_sessions_to_site, total_sessions,
#          sessions_per_1000_all, minutes_on_site, total_minutes, minutes_per_1000_all

import pandas as pd
from pathlib import Path
import os
import sys

# Config
DATA_DIR = Path("data/ProcessComscore")
OUTPUT_DIR = Path("output/descriptives")

MAJOR_SITES = ["pornhub", "xvideos", "xnxx", "xhamster", "chaturbate"]

# Month range: Jan 2022 to Dec 2024
MONTHS = []
for year in range(2022, 2025):
    for month in range(1, 13):
        MONTHS.append(f"{year}{month:02d}")


def process_month(yyyymm: str) -> list:
    """Process a single month of mobile data and return a list of result dicts (one per site)."""
    session_path = DATA_DIR / "merged_session_files" / f"merged_mobile_sessions_{yyyymm}.parquet"
    if not session_path.exists():
        print(f"  WARNING: Mobile session file not found for {yyyymm}, skipping.")
        return []

    print(f"  Loading {session_path.name}...")
    df = pd.read_parquet(session_path, columns=['top_web_name', 'duration'])

    df['top_web_name_lower'] = df['top_web_name'].str.lower()
    total_sessions = len(df)
    total_minutes = df['duration'].sum() / 60.0

    print(f"  Total sessions: {total_sessions:,} | Total minutes: {total_minutes:,.0f}")

    results = []
    for site in MAJOR_SITES:
        site_mask = df['top_web_name_lower'].str.contains(site, na=False)
        site_count = site_mask.sum()
        per_1000_all = (site_count / total_sessions) * 1000 if total_sessions > 0 else 0.0

        site_minutes = df.loc[site_mask, 'duration'].sum() / 60.0
        minutes_per_1000 = (site_minutes / total_minutes) * 1000 if total_minutes > 0 else 0.0

        results.append({
            'month': yyyymm,
            'site': site,
            'all_sessions_to_site': int(site_count),
            'total_sessions': int(total_sessions),
            'sessions_per_1000_all': round(per_1000_all, 6),
            'minutes_on_site': round(site_minutes, 2),
            'total_minutes': round(total_minutes, 2),
            'minutes_per_1000_all': round(minutes_per_1000, 6),
        })

    return results


def main():
    print("=" * 60)
    print("VALIDATE GOOGLE TRENDS - MOBILE")
    print("Sessions and minutes on adult sites per 1,000 (mobile)")
    print("Note: Google-referred metric unavailable for mobile data")
    print("=" * 60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_results = []
    for yyyymm in MONTHS:
        print(f"\nProcessing {yyyymm}...")
        month_results = process_month(yyyymm)
        all_results.extend(month_results)

    if not all_results:
        print("\nNo results produced. Check that mobile data files exist.")
        sys.exit(1)

    results_df = pd.DataFrame(all_results)
    output_path = OUTPUT_DIR / "validate_googletrends_mobile.csv"
    results_df.to_csv(output_path, index=False)

    print(f"\n{'=' * 60}")
    print(f"Output saved to: {output_path}")
    print(f"Total rows: {len(results_df)} ({len(MONTHS)} months x {len(MAJOR_SITES)} sites)")
    print(f"{'=' * 60}")

    # Print summary table
    pivot = results_df.pivot(index='month', columns='site', values='sessions_per_1000_all')
    pivot = pivot[MAJOR_SITES]
    print("\nSessions per 1,000 total mobile sessions:")
    print(pivot.to_string())


if __name__ == "__main__":
    main()
