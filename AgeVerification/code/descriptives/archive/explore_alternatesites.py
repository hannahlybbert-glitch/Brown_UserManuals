#!/usr/bin/env python3
# Author: Emily
# Created: 2026-01-30
# Purpose: Analyze traffic on sites that contain major porn site names in their URLs
#          to understand how much traffic comes from the main site vs. affiliated/copycat sites.
# Inputs (internal): merged session parquet files
# Outputs: Summary tables and bar charts showing traffic breakdown for each major site

import sys
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

import os

# Set working directory to local git repo
os.chdir("/Users/emilydavis/Documents/gitrepos/AgeVerification")

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'code'))

from plot_style import apply_plot_style, UCHICAGO_MAROON

# Config
DATA_DIR = Path("data/ProcessComscore")
OUTPUT_DIR = Path("output/descriptives")

# Month configurations: (month_id, session_file_suffix)
MONTHS = [
    (265, "202201"),
    (300, "202412"),
]

# Major sites to analyze: (keyword, flagship_domain)
MAJOR_SITES = [
    ("pornhub", "pornhub.com"),
    ("xvideos", "xvideos.com"),
    ("xnxx", "xnxx.com"),
    ("xhamster", "xhamster.com"),
    ("chaturbate", "chaturbate.com"),
]


def load_sessions(session_suffix: str) -> pd.DataFrame:
    """Load merged sessions parquet file."""
    session_path = DATA_DIR / "merged_session_files" / f"merged_sessions_{session_suffix}.parquet"
    if not session_path.exists():
        raise FileNotFoundError(f"Session file not found: {session_path}")

    print(f"Loading sessions from: {session_path}")
    df = pd.read_parquet(session_path)
    print(f"  Loaded {len(df):,} sessions")
    return df


def plot_site_breakdown_dual(keyword: str, flagship: str, month_data: list, top_n: int = 10):
    """
    Create dual-panel horizontal bar chart showing traffic breakdown for a major site.

    Each panel shows one month. Bars (top to bottom):
    1. All sites containing keyword (total)
    2. Flagship site (e.g., pornhub.com)
    3-12. Top 10 other sites
    13. All other sites
    """
    apply_plot_style()

    fig, axes = plt.subplots(1, 2, figsize=(16, 8))

    for idx, (ax, data) in enumerate(zip(axes, month_data)):
        session_suffix = data['session_suffix']
        all_minutes = data['all_minutes']
        flagship_minutes = data['flagship_minutes']
        other_sites_df = data['other_sites_df']

        # Get top N other sites
        top_other = other_sites_df.head(top_n).copy()

        # Calculate "all other" (sites not in top N, excluding flagship)
        top_other_minutes = top_other['total_minutes'].sum()
        other_minutes = all_minutes - flagship_minutes - top_other_minutes

        # Build plot data
        labels = []
        values = []
        colors = []

        # 1. All sites (total)
        labels.append(f'All "{keyword}" sites')
        values.append(all_minutes)
        colors.append('#767676')  # Gray for total

        # 2. Flagship site
        labels.append(f'{flagship.upper()} (flagship)')
        values.append(flagship_minutes)
        colors.append(UCHICAGO_MAROON)

        # 3-12. Top other sites
        for _, row in top_other.iterrows():
            labels.append(row['top_web_name'])
            values.append(row['total_minutes'])
            colors.append(UCHICAGO_MAROON)

        # 13. All other sites
        if other_minutes > 0:
            labels.append('All other sites')
            values.append(other_minutes)
            colors.append('#767676')  # Gray

        # Convert to hours for readability
        values_hours = [v / 60 for v in values]

        y_pos = range(len(labels))
        bars = ax.barh(y_pos, values_hours, color=colors)

        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=9)
        ax.invert_yaxis()
        ax.set_xlabel('Total Hours')
        ax.set_title(f'Month: {session_suffix}', fontsize=12)

        # Add value labels on bars
        max_val = max(values_hours) if values_hours else 1
        for bar, val in zip(bars, values_hours):
            width = bar.get_width()
            ax.text(width + max_val * 0.01, bar.get_y() + bar.get_height()/2,
                    f'{val:,.0f}h', va='center', fontsize=8)

    fig.suptitle(f'Traffic Breakdown: Sites Containing "{keyword}"', fontsize=14, y=1.02)
    plt.tight_layout()

    # Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f'alternate_sites_{keyword}.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  Chart saved to: {output_path}")


def analyze_major_site(sessions: pd.DataFrame, keyword: str, flagship: str,
                       session_suffix: str) -> dict:
    """Analyze traffic for sites containing a major site's name."""

    # Normalize names for matching
    sessions_lower = sessions['top_web_name'].str.lower()

    # Find all sites containing the keyword
    mask_keyword = sessions_lower.str.contains(keyword, na=False)
    keyword_sessions = sessions[mask_keyword]

    if len(keyword_sessions) == 0:
        print(f"  No sessions found for keyword: {keyword}")
        return None

    # Calculate total traffic for all sites with keyword
    all_minutes = keyword_sessions['duration_minutes'].sum()
    all_session_count = len(keyword_sessions)

    # Find flagship site traffic
    mask_flagship = sessions_lower == flagship.lower()
    flagship_sessions = sessions[mask_flagship]
    flagship_minutes = flagship_sessions['duration_minutes'].sum()
    flagship_session_count = len(flagship_sessions)

    # Find other sites (contain keyword but not the flagship)
    mask_other = mask_keyword & ~mask_flagship
    other_sessions = sessions[mask_other]
    other_minutes = other_sessions['duration_minutes'].sum()
    other_session_count = len(other_sessions)

    # Get breakdown of other sites
    other_by_site = other_sessions.groupby('top_web_name').agg(
        sessions=('duration', 'size'),
        total_minutes=('duration_minutes', 'sum')
    ).reset_index()
    other_by_site = other_by_site.sort_values('total_minutes', ascending=False)

    # Print summary
    print(f"\n  ## {keyword.upper()} Sites\n")
    print(f"  | Category | Sessions | Minutes | % of Total |")
    print(f"  |----------|----------|---------|------------|")
    print(f"  | All '{keyword}' sites | {all_session_count:,} | {all_minutes:,.0f} | 100% |")
    print(f"  | {flagship} (flagship) | {flagship_session_count:,} | {flagship_minutes:,.0f} | {100*flagship_minutes/all_minutes:.1f}% |")
    print(f"  | Other sites | {other_session_count:,} | {other_minutes:,.0f} | {100*other_minutes/all_minutes:.1f}% |")

    # Print top other sites
    if len(other_by_site) > 0:
        print(f"\n  Top 10 other sites containing '{keyword}':\n")
        print(f"  | Rank | Site | Sessions | Minutes | % of Total |")
        print(f"  |------|------|----------|---------|------------|")
        for i, (_, row) in enumerate(other_by_site.head(10).iterrows(), 1):
            pct = 100 * row['total_minutes'] / all_minutes
            print(f"  | {i} | {row['top_web_name']} | {row['sessions']:,} | {row['total_minutes']:,.0f} | {pct:.2f}% |")

    return {
        'keyword': keyword,
        'flagship': flagship,
        'session_suffix': session_suffix,
        'all_minutes': all_minutes,
        'flagship_minutes': flagship_minutes,
        'other_minutes': other_minutes,
        'other_sites_df': other_by_site,
        'flagship_pct': 100 * flagship_minutes / all_minutes if all_minutes > 0 else 0,
        'num_other_sites': len(other_by_site),
    }


def analyze_month(month_id: int, session_suffix: str):
    """Analyze alternate sites for all major sites in a single month."""

    print(f"\n{'='*70}")
    print(f"MONTH {month_id} (Session file: {session_suffix})")
    print(f"{'='*70}")

    # Load data
    sessions = load_sessions(session_suffix)

    # Convert duration to minutes
    sessions['duration_minutes'] = sessions['duration'] / 60

    results = []
    for keyword, flagship in MAJOR_SITES:
        result = analyze_major_site(sessions, keyword, flagship, session_suffix)
        if result:
            results.append(result)

    # Summary table
    if results:
        print(f"\n{'='*70}")
        print("SUMMARY: Flagship Site Share of Total Keyword Traffic")
        print(f"{'='*70}\n")
        print("| Keyword | Total Hours | Flagship Hours | Flagship % | Other Sites |")
        print("|---------|-------------|----------------|------------|-------------|")
        for r in results:
            total_hours = r['all_minutes'] / 60
            flagship_hours = r['flagship_minutes'] / 60
            print(f"| {r['keyword']} | {total_hours:,.0f} | {flagship_hours:,.0f} | {r['flagship_pct']:.1f}% | {r['num_other_sites']:,} |")

    return results


def main():
    print("=" * 70)
    print("ALTERNATE SITES ANALYSIS")
    print("Analyzing traffic on sites containing major porn site names")
    print("=" * 70)

    all_results = {}
    for month_id, session_suffix in MONTHS:
        try:
            results = analyze_month(month_id, session_suffix)
            all_results[session_suffix] = results
        except FileNotFoundError as e:
            print(f"\nSkipping month {month_id}: {e}")

    # Create combined charts for each keyword (both months in one figure)
    if len(all_results) >= 2:
        print(f"\n{'='*70}")
        print("CREATING COMBINED CHARTS")
        print(f"{'='*70}")

        for keyword, flagship in MAJOR_SITES:
            # Collect data for this keyword from all months
            month_data = []
            for session_suffix, results in all_results.items():
                result = next((r for r in results if r['keyword'] == keyword), None)
                if result:
                    month_data.append(result)

            if len(month_data) == 2:
                plot_site_breakdown_dual(keyword, flagship, month_data)

    # Cross-month comparison
    if len(all_results) > 1:
        print(f"\n{'='*70}")
        print("CROSS-MONTH COMPARISON: Flagship Share")
        print(f"{'='*70}\n")

        # Get keywords from first month
        first_month = list(all_results.keys())[0]
        keywords = [r['keyword'] for r in all_results[first_month]]

        print("| Keyword | " + " | ".join(all_results.keys()) + " |")
        print("|---------|" + "|".join(["----------"] * len(all_results)) + "|")

        for keyword in keywords:
            row = f"| {keyword} |"
            for month, results in all_results.items():
                result = next((r for r in results if r['keyword'] == keyword), None)
                if result:
                    row += f" {result['flagship_pct']:.1f}% |"
                else:
                    row += " - |"
            print(row)

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
