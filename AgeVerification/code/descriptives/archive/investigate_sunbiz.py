"""
Investigate SUNBIZ.ORG anomaly across months.

SUNBIZ.ORG appears as #12 in Jan 2022 but drops out of top 500 by Feb 2023.
This script investigates the pattern_ids, web characteristics, and traffic
patterns to understand what's happening.

Usage:
    python code/descriptives/investigate_sunbiz.py

Outputs:
    - output/descriptives/sunbiz_investigation.txt
"""

import pandas as pd
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path.cwd()
DATA_DIR = BASE_DIR / 'data' / 'ProcessComscore'
OUTPUT_DIR = BASE_DIR / 'output' / 'descriptives'

# Month configurations
MONTHS = {
    '202201': {'label': 'Jan 2022', 'month_id': '265'},
    '202202': {'label': 'Feb 2022', 'month_id': '266'},
    '202302': {'label': 'Feb 2023', 'month_id': None},  # No intermediate files
}


def investigate_web_characteristics():
    """Check SUNBIZ entries in web_characteristics files."""
    results = []
    results.append("=" * 80)
    results.append("WEB CHARACTERISTICS FILES")
    results.append("=" * 80)

    for month_id in ['265', '266']:
        web_char_path = DATA_DIR / 'intermediate' / month_id / 'web_characteristics.parquet'
        if web_char_path.exists():
            df = pd.read_parquet(web_char_path)
            sunbiz = df[df['top_web_name'].str.contains('SUNBIZ', case=False, na=False)]

            results.append(f"\nMonth ID {month_id}:")
            results.append(f"  Total websites: {len(df):,}")
            results.append(f"  SUNBIZ entries: {len(sunbiz)}")
            if len(sunbiz) > 0:
                for _, row in sunbiz.iterrows():
                    results.append(f"    - top_web_id: {row['top_web_id']}, name: {row['top_web_name']}, "
                                   f"category: {row['category']}, subcategory: {row['subcategory']}")

    return results


def investigate_crosswalks():
    """Check pattern_ids mapping to SUNBIZ in crosswalk files."""
    results = []
    results.append("\n" + "=" * 80)
    results.append("CROSSWALK FILES (pattern_id -> top_web_id mappings)")
    results.append("=" * 80)

    # First get SUNBIZ top_web_ids from web_characteristics
    sunbiz_web_ids = set()
    for month_id in ['265', '266']:
        web_char_path = DATA_DIR / 'intermediate' / month_id / 'web_characteristics.parquet'
        if web_char_path.exists():
            df = pd.read_parquet(web_char_path)
            sunbiz = df[df['top_web_name'].str.contains('SUNBIZ', case=False, na=False)]
            sunbiz_web_ids.update(sunbiz['top_web_id'].astype(str).tolist())

    results.append(f"\nSUNBIZ top_web_ids found: {sunbiz_web_ids}")

    for month_id in ['265', '266']:
        xw_path = DATA_DIR / 'intermediate' / month_id / 'crosswalk.parquet'
        if xw_path.exists():
            df = pd.read_parquet(xw_path)
            df['top_web_id'] = df['top_web_id'].astype(str)

            # Find pattern_ids mapping to SUNBIZ
            sunbiz_patterns = df[df['top_web_id'].isin(sunbiz_web_ids)]

            results.append(f"\nMonth ID {month_id}:")
            results.append(f"  Total pattern_ids: {len(df):,}")
            results.append(f"  Pattern_ids mapping to SUNBIZ: {len(sunbiz_patterns)}")
            if len(sunbiz_patterns) > 0:
                for _, row in sunbiz_patterns.iterrows():
                    results.append(f"    - pattern_id: {row['pattern_id']} -> top_web_id: {row['top_web_id']}")

    return results


def investigate_session_traffic():
    """Analyze SUNBIZ traffic in merged session files."""
    results = []
    results.append("\n" + "=" * 80)
    results.append("SESSION TRAFFIC ANALYSIS")
    results.append("=" * 80)

    for month, config in MONTHS.items():
        session_path = DATA_DIR / 'merged_session_files' / f'merged_sessions_{month}.parquet'
        if not session_path.exists():
            results.append(f"\n{config['label']}: File not found")
            continue

        logger.info(f"Loading {config['label']}...")
        df = pd.read_parquet(session_path)
        total_sessions = len(df)

        # Find SUNBIZ sessions
        sunbiz = df[df['top_web_name'].str.contains('SUNBIZ', case=False, na=False)]

        results.append(f"\n{config['label']} ({month}):")
        results.append(f"  Total sessions: {total_sessions:,}")
        results.append(f"  SUNBIZ sessions: {len(sunbiz):,} ({len(sunbiz)/total_sessions*100:.4f}%)")

        if len(sunbiz) > 0:
            # Breakdown by top_web_name
            results.append(f"\n  Breakdown by top_web_name:")
            for name, group in sunbiz.groupby('top_web_name'):
                results.append(f"    - {name}: {len(group):,} sessions")

            # Focus on SUNBIZ.ORG specifically
            sunbiz_org = df[df['top_web_name'] == 'SUNBIZ.ORG']
            if len(sunbiz_org) > 0:
                results.append(f"\n  SUNBIZ.ORG details:")
                results.append(f"    Sessions: {len(sunbiz_org):,}")
                results.append(f"    Unique machines: {sunbiz_org['machine_id'].nunique():,}")
                results.append(f"    Unique persons: {sunbiz_org['person_id'].nunique():,}")
                results.append(f"    Unique pattern_ids: {sunbiz_org['pattern_id'].nunique()}")
                results.append(f"    Pattern_ids: {sunbiz_org['pattern_id'].unique().tolist()}")

                # Duration stats
                results.append(f"    Mean duration (min): {sunbiz_org['duration'].mean()/60:.2f}")
                results.append(f"    Median duration (min): {sunbiz_org['duration'].median()/60:.2f}")
                results.append(f"    Zero-duration sessions: {(sunbiz_org['duration']==0).sum()} ({(sunbiz_org['duration']==0).sum()/len(sunbiz_org)*100:.1f}%)")

                # Category info
                results.append(f"    Category: {sunbiz_org['category'].iloc[0]}")
                results.append(f"    Subcategory: {sunbiz_org['subcategory'].iloc[0]}")

                # Top metro areas
                results.append(f"\n    Top 5 metro areas:")
                metros = sunbiz_org['metro_area'].value_counts().head(5)
                for metro, count in metros.items():
                    results.append(f"      - {metro}: {count:,}")

    return results


def investigate_pattern_id_across_months():
    """Check if the same pattern_id appears in multiple months with different mappings."""
    results = []
    results.append("\n" + "=" * 80)
    results.append("PATTERN_ID CONSISTENCY CHECK")
    results.append("=" * 80)

    # Get SUNBIZ pattern_ids from sessions
    pattern_ids_by_month = {}
    for month, config in MONTHS.items():
        session_path = DATA_DIR / 'merged_session_files' / f'merged_sessions_{month}.parquet'
        if session_path.exists():
            df = pd.read_parquet(session_path, columns=['top_web_name', 'pattern_id'])
            sunbiz_org = df[df['top_web_name'] == 'SUNBIZ.ORG']
            pattern_ids_by_month[month] = set(sunbiz_org['pattern_id'].unique())

    results.append("\nPattern_ids mapped to SUNBIZ.ORG by month:")
    for month, pids in pattern_ids_by_month.items():
        results.append(f"  {month}: {pids}")

    # Check overlap
    if len(pattern_ids_by_month) >= 2:
        all_pids = set()
        for pids in pattern_ids_by_month.values():
            all_pids.update(pids)

        results.append(f"\nAll unique pattern_ids: {all_pids}")

        # For each pattern_id, check what it maps to in each month
        results.append("\nChecking each pattern_id across months:")
        for pid in all_pids:
            results.append(f"\n  pattern_id {pid}:")
            for month, config in MONTHS.items():
                session_path = DATA_DIR / 'merged_session_files' / f'merged_sessions_{month}.parquet'
                if session_path.exists():
                    df = pd.read_parquet(session_path, columns=['pattern_id', 'top_web_name', 'session_id'])
                    matches = df[df['pattern_id'] == str(pid)]
                    if len(matches) > 0:
                        names = matches['top_web_name'].unique()
                        results.append(f"    {config['label']}: {len(matches):,} sessions -> {names.tolist()}")
                    else:
                        results.append(f"    {config['label']}: 0 sessions")

    return results


def main():
    """Run all investigations and save results."""
    logger.info("Starting SUNBIZ.ORG investigation...")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_results = []
    all_results.append("SUNBIZ.ORG INVESTIGATION REPORT")
    all_results.append("=" * 80)
    all_results.append("")

    # Run investigations
    all_results.extend(investigate_web_characteristics())
    all_results.extend(investigate_crosswalks())
    all_results.extend(investigate_session_traffic())
    all_results.extend(investigate_pattern_id_across_months())

    # Save results
    output_path = OUTPUT_DIR / 'sunbiz_investigation.txt'
    with open(output_path, 'w') as f:
        f.write('\n'.join(all_results))

    logger.info(f"Results saved to: {output_path}")

    # Also print to console
    print('\n'.join(all_results))


if __name__ == "__main__":
    main()
