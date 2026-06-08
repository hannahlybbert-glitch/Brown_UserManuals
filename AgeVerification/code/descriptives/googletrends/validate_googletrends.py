#!/usr/bin/env python3
# Author: Emily
# Created: 2026-02-14
# Purpose: For each month (Jan 2022 - Dec 2024), compute:
#          1. Google-referred sessions to each major adult site per 1,000 Google-referred sessions
#          2. All sessions to each site per 1,000 total sessions
#          3. Minutes on each site per 1,000 total minutes
# Inputs: merged session parquet files, crosswalk files
# Outputs: CSV with columns: month, site, google_sessions_to_site, total_google_sessions,
#          sessions_per_1000_google, all_sessions_to_site, total_sessions,
#          sessions_per_1000_all, minutes_on_site, total_minutes, minutes_per_1000_all

import pandas as pd
from pathlib import Path
import os
import sys

# Config
DATA_DIR = Path("data/ProcessComscore")
OUTPUT_DIR = Path("output/descriptives")

GOOGLE_TOP_WEB_ID = '590133'

MAJOR_SITES = ["pornhub", "xvideos", "xnxx", "xhamster", "chaturbate"]

# Month range: Jan 2022 to Dec 2024
MONTHS = []
for year in range(2022, 2025):
    for month in range(1, 13):
        MONTHS.append(f"{year}{month:02d}")


def yyyymm_to_month_id(yyyymm: str) -> int:
    """Convert YYYYMM string to Comscore internal month_id.
    month_id 265 = 202201, increments by 1 each month."""
    year = int(yyyymm[:4])
    month = int(yyyymm[4:])
    return 265 + (year - 2022) * 12 + (month - 1)


def process_month(yyyymm: str) -> list:
    """Process a single month and return a list of result dicts (one per site)."""
    month_id = yyyymm_to_month_id(yyyymm)

    # Load crosswalk to get Google pattern_ids
    crosswalk_path = DATA_DIR / "intermediate" / str(month_id) / "crosswalk.parquet"
    if not crosswalk_path.exists():
        print(f"  WARNING: Crosswalk not found for {yyyymm} (month_id {month_id}), skipping.")
        return []

    crosswalk = pd.read_parquet(crosswalk_path)
    crosswalk['top_web_id'] = crosswalk['top_web_id'].astype(str)
    crosswalk['pattern_id'] = crosswalk['pattern_id'].astype(str)
    google_patterns = set(crosswalk[crosswalk['top_web_id'] == GOOGLE_TOP_WEB_ID]['pattern_id'])

    # Load merged sessions
    session_path = DATA_DIR / "merged_session_files" / f"merged_sessions_{yyyymm}.parquet"
    if not session_path.exists():
        print(f"  WARNING: Session file not found for {yyyymm}, skipping.")
        return []

    print(f"  Loading {session_path.name}...")
    df = pd.read_parquet(session_path, columns=['ref_pattern_id', 'top_web_name', 'duration'])

    # Precompute lowercase site names and total stats
    df['top_web_name_lower'] = df['top_web_name'].str.lower()
    total_sessions = len(df)
    total_minutes = df['duration'].sum() / 60.0

    # Identify Google-referred sessions
    df['ref_pattern_id'] = df['ref_pattern_id'].astype(str)
    google_mask = df['ref_pattern_id'].isin(google_patterns)
    google_df = df[google_mask]
    total_google = len(google_df)

    if total_google == 0:
        print(f"  WARNING: No Google-referred sessions found for {yyyymm}, skipping.")
        return []

    print(f"  Total sessions: {total_sessions:,} | Google-referred: {total_google:,}")

    results = []
    for site in MAJOR_SITES:
        # Google-referred sessions to site
        google_site_mask = google_df['top_web_name_lower'].str.contains(site, na=False)
        google_site_count = google_site_mask.sum()
        per_1000_google = (google_site_count / total_google) * 1000

        # All sessions to site
        all_site_mask = df['top_web_name_lower'].str.contains(site, na=False)
        all_site_count = all_site_mask.sum()
        per_1000_all = (all_site_count / total_sessions) * 1000

        # Minutes on site
        site_minutes = df.loc[all_site_mask, 'duration'].sum() / 60.0
        minutes_per_1000 = (site_minutes / total_minutes) * 1000

        results.append({
            'month': yyyymm,
            'site': site,
            'google_sessions_to_site': int(google_site_count),
            'total_google_sessions': int(total_google),
            'sessions_per_1000_google': round(per_1000_google, 6),
            'all_sessions_to_site': int(all_site_count),
            'total_sessions': int(total_sessions),
            'sessions_per_1000_all': round(per_1000_all, 6),
            'minutes_on_site': round(site_minutes, 2),
            'total_minutes': round(total_minutes, 2),
            'minutes_per_1000_all': round(minutes_per_1000, 6),
        })

    return results


def main():
    print("=" * 60)
    print("VALIDATE GOOGLE TRENDS")
    print("Google-referred sessions to adult sites per 1,000 Google sessions")
    print("=" * 60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_results = []
    for yyyymm in MONTHS:
        print(f"\nProcessing {yyyymm}...")
        month_results = process_month(yyyymm)
        all_results.extend(month_results)

    if not all_results:
        print("\nNo results produced. Check that data files exist.")
        sys.exit(1)

    # Create output CSV
    results_df = pd.DataFrame(all_results)
    output_path = OUTPUT_DIR / "validate_googletrends.csv"
    results_df.to_csv(output_path, index=False)

    print(f"\n{'=' * 60}")
    print(f"Output saved to: {output_path}")
    print(f"Total rows: {len(results_df)} ({len(MONTHS)} months x {len(MAJOR_SITES)} sites)")
    print(f"{'=' * 60}")

    # Print summary table
    pivot = results_df.pivot(index='month', columns='site', values='sessions_per_1000_google')
    pivot = pivot[MAJOR_SITES]
    print("\nSessions per 1,000 Google-referred sessions:")
    print(pivot.to_string())


if __name__ == "__main__":
    main()
