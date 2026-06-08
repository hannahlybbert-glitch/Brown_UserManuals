#!/usr/bin/env python3
# Author: Emily
# Created: 2026-02-02
# Purpose: Analyze sequential sessions to see if people visit Google before adult sites.
#          Unlike investigate_googlesearch.py which uses referrer IDs, this looks at
#          the actual previous session for each user to identify search-to-adult patterns.
# Inputs: merged session parquet files, crosswalk files
# Outputs: Summary tables showing share of adult sessions preceded by search engine visits

import pandas as pd
from pathlib import Path
import os

# Set working directory to local git repo
os.chdir("/Users/emilydavis/Documents/gitrepos/AgeVerification")

# Config
DATA_DIR = Path("data/ProcessComscore")
OUTPUT_DIR = Path("output/descriptives")

# Month configurations: (month_id, session_file_suffix)
MONTHS = [
    (265, "202201"),
    (300, "202412"),
]

# Time gap thresholds (in seconds)
MAX_GAP_SECONDS = 30 * 60  # 30 minutes

# Search engine top_web_ids
GOOGLE_TOP_WEB_ID = '590133'
MICROSOFT_TOP_WEB_ID = '11320'  # Microsoft Sites (includes Bing)


def load_sessions(session_suffix: str) -> pd.DataFrame:
    """Load merged sessions parquet file."""
    session_path = DATA_DIR / "merged_session_files" / f"merged_sessions_{session_suffix}.parquet"
    if not session_path.exists():
        raise FileNotFoundError(f"Session file not found: {session_path}")

    print(f"Loading sessions from: {session_path}")
    df = pd.read_parquet(session_path)
    print(f"  Loaded {len(df):,} sessions")
    return df


def add_previous_session_info(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each session, add information about the previous session for the same person.
    Sessions are ordered by first_ss2k (start time in seconds since 2000).
    """
    print("  Sorting sessions by person and time...")
    df = df.sort_values(['person_id', 'first_ss2k']).reset_index(drop=True)

    print("  Computing previous session info...")
    # Shift to get previous session's values within each person
    df['prev_top_web_id'] = df.groupby('person_id')['top_web_id'].shift(1)
    df['prev_top_web_name'] = df.groupby('person_id')['top_web_name'].shift(1)
    df['prev_subcategory'] = df.groupby('person_id')['subcategory'].shift(1)
    df['prev_first_ss2k'] = df.groupby('person_id')['first_ss2k'].shift(1)
    df['prev_duration'] = df.groupby('person_id')['duration'].shift(1)

    # Calculate time gap between sessions
    # Gap = start of current session - (start of previous session + duration of previous session)
    df['time_gap_seconds'] = df['first_ss2k'] - (df['prev_first_ss2k'] + df['prev_duration'].fillna(0))

    return df


def analyze_month(month_id: int, session_suffix: str) -> dict:
    """Analyze sequential session patterns for a single month."""

    print(f"\n{'='*60}")
    print(f"Processing month {month_id} ({session_suffix})...")
    print(f"{'='*60}")

    # Load sessions
    df = load_sessions(session_suffix)

    # Add previous session info
    df = add_previous_session_info(df)

    # Identify session types
    df['is_xxx_adult'] = df['subcategory'] == 'XXX Adult'
    df['prev_is_google'] = df['prev_top_web_id'].astype(str) == GOOGLE_TOP_WEB_ID
    df['prev_is_microsoft'] = df['prev_top_web_id'].astype(str) == MICROSOFT_TOP_WEB_ID
    df['prev_is_search'] = df['prev_is_google'] | df['prev_is_microsoft']

    # Filter to XXX Adult sessions only
    xxx_df = df[df['is_xxx_adult']].copy()
    print(f"\n  XXX Adult sessions: {len(xxx_df):,}")

    # Basic stats (all XXX sessions)
    total_xxx = len(xxx_df)
    xxx_with_prev = xxx_df['prev_top_web_id'].notna().sum()

    # Stats for sessions with previous session (any time gap)
    xxx_prev_google_any = xxx_df['prev_is_google'].sum()
    xxx_prev_microsoft_any = xxx_df['prev_is_microsoft'].sum()
    xxx_prev_search_any = xxx_df['prev_is_search'].sum()

    # Stats for sessions within 30 minutes
    xxx_within_30 = xxx_df[xxx_df['time_gap_seconds'] <= MAX_GAP_SECONDS].copy()
    xxx_within_30_count = len(xxx_within_30)
    xxx_30_prev_google = xxx_within_30['prev_is_google'].sum()
    xxx_30_prev_microsoft = xxx_within_30['prev_is_microsoft'].sum()
    xxx_30_prev_search = xxx_within_30['prev_is_search'].sum()

    # Stats for tighter time windows
    time_windows = [5, 10, 15, 30]  # minutes
    window_results = {}
    for minutes in time_windows:
        seconds = minutes * 60
        subset = xxx_df[xxx_df['time_gap_seconds'] <= seconds]
        window_results[minutes] = {
            'total': len(subset),
            'prev_google': subset['prev_is_google'].sum(),
            'prev_microsoft': subset['prev_is_microsoft'].sum(),
            'prev_search': subset['prev_is_search'].sum(),
        }

    # What sites do people visit just before XXX Adult? (within 30 min)
    prev_site_counts = xxx_within_30['prev_top_web_name'].value_counts().head(20).to_dict()
    prev_subcat_counts = xxx_within_30['prev_subcategory'].value_counts().head(15).to_dict()

    # Distribution of time gaps for XXX sessions
    xxx_with_gap = xxx_df[xxx_df['time_gap_seconds'].notna() & (xxx_df['time_gap_seconds'] >= 0)]
    gap_percentiles = xxx_with_gap['time_gap_seconds'].quantile([0.25, 0.5, 0.75, 0.9, 0.95]).to_dict()

    return {
        'month_id': month_id,
        'session_suffix': session_suffix,
        'total_xxx': total_xxx,
        'xxx_with_prev': xxx_with_prev,
        'xxx_prev_google_any': xxx_prev_google_any,
        'xxx_prev_microsoft_any': xxx_prev_microsoft_any,
        'xxx_prev_search_any': xxx_prev_search_any,
        'xxx_within_30_count': xxx_within_30_count,
        'xxx_30_prev_google': xxx_30_prev_google,
        'xxx_30_prev_microsoft': xxx_30_prev_microsoft,
        'xxx_30_prev_search': xxx_30_prev_search,
        'window_results': window_results,
        'prev_site_counts': prev_site_counts,
        'prev_subcat_counts': prev_subcat_counts,
        'gap_percentiles': gap_percentiles,
    }


def print_results(results: list):
    """Print analysis results."""

    for r in results:
        m = r['session_suffix']

        print(f"\n{'='*70}")
        print(f"SEQUENTIAL SESSION ANALYSIS - {m}")
        print(f"{'='*70}")

        print(f"\n--- OVERVIEW ---")
        print(f"Total XXX Adult sessions: {r['total_xxx']:,}")
        print(f"XXX sessions with a previous session: {r['xxx_with_prev']:,}")

        print(f"\n--- TIME GAP DISTRIBUTION (for XXX sessions) ---")
        print(f"25th percentile: {r['gap_percentiles'][0.25]/60:.1f} minutes")
        print(f"50th percentile (median): {r['gap_percentiles'][0.5]/60:.1f} minutes")
        print(f"75th percentile: {r['gap_percentiles'][0.75]/60:.1f} minutes")
        print(f"90th percentile: {r['gap_percentiles'][0.9]/60:.1f} minutes")
        print(f"95th percentile: {r['gap_percentiles'][0.95]/60:.1f} minutes")

        print(f"\n--- PREVIOUS SESSION FROM SEARCH ENGINE (any time gap) ---")
        pct_google = 100 * r['xxx_prev_google_any'] / r['xxx_with_prev'] if r['xxx_with_prev'] > 0 else 0
        pct_msft = 100 * r['xxx_prev_microsoft_any'] / r['xxx_with_prev'] if r['xxx_with_prev'] > 0 else 0
        pct_search = 100 * r['xxx_prev_search_any'] / r['xxx_with_prev'] if r['xxx_with_prev'] > 0 else 0
        print(f"Previous session was Google: {r['xxx_prev_google_any']:,} ({pct_google:.2f}%)")
        print(f"Previous session was Microsoft: {r['xxx_prev_microsoft_any']:,} ({pct_msft:.2f}%)")
        print(f"Previous session was any search: {r['xxx_prev_search_any']:,} ({pct_search:.2f}%)")

        print(f"\n--- BY TIME WINDOW ---")
        print(f"| Time Window | XXX Sessions | Prev=Google | % | Prev=Microsoft | % | Prev=Search | % |")
        print(f"|-------------|--------------|-------------|---|----------------|---|-------------|---|")
        for minutes in [5, 10, 15, 30]:
            w = r['window_results'][minutes]
            if w['total'] > 0:
                pct_g = 100 * w['prev_google'] / w['total']
                pct_m = 100 * w['prev_microsoft'] / w['total']
                pct_s = 100 * w['prev_search'] / w['total']
            else:
                pct_g = pct_m = pct_s = 0
            print(f"| <= {minutes} min | {w['total']:,} | {w['prev_google']:,} | {pct_g:.2f}% | {w['prev_microsoft']:,} | {pct_m:.2f}% | {w['prev_search']:,} | {pct_s:.2f}% |")

        print(f"\n--- TOP PREVIOUS SITES (within 30 min of XXX session) ---")
        print(f"| Rank | Previous Site | Count | % |")
        print(f"|------|---------------|-------|---|")
        total_30 = r['xxx_within_30_count']
        for i, (site, count) in enumerate(r['prev_site_counts'].items(), 1):
            pct = 100 * count / total_30 if total_30 > 0 else 0
            site_name = site if pd.notna(site) else "(No previous session)"
            print(f"| {i} | {site_name} | {count:,} | {pct:.2f}% |")

        print(f"\n--- TOP PREVIOUS SUBCATEGORIES (within 30 min of XXX session) ---")
        print(f"| Rank | Previous Subcategory | Count | % |")
        print(f"|------|----------------------|-------|---|")
        for i, (subcat, count) in enumerate(r['prev_subcat_counts'].items(), 1):
            pct = 100 * count / total_30 if total_30 > 0 else 0
            subcat_name = subcat if pd.notna(subcat) else "(No previous session)"
            print(f"| {i} | {subcat_name} | {count:,} | {pct:.2f}% |")


def main():
    print("=" * 70)
    print("SEQUENTIAL SESSION ANALYSIS")
    print("Analyzing whether users visit search engines before adult sites")
    print("(Looking at actual previous session, not just referrer)")
    print("=" * 70)

    results = []
    for month_id, session_suffix in MONTHS:
        try:
            result = analyze_month(month_id, session_suffix)
            results.append(result)
        except FileNotFoundError as e:
            print(f"\nSkipping month {month_id}: {e}")

    if results:
        print_results(results)

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
