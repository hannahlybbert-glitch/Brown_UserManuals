#!/usr/bin/env python3
# Author: Emily
# Created: 2026-01-26
# Purpose: Analyze traffic on Category 3 sites (in GitHub porn list, in Comscore, but not classified as XXX Adult)
#          to assess how relevant these potentially misclassified sites are compared to XXX Adult sites.
# Inputs (internal): data/analysis/category3_{month}.csv, merged session parquet files
# Outputs: Summary tables comparing Category 3 traffic to XXX Adult traffic; bar charts of top Category 3 sites

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
ANALYSIS_DIR = Path("data/analysis")
OUTPUT_DIR = Path("output/descriptives")

# Month configurations: (month_id, session_file_suffix)
MONTHS = [
    (265, "202201"),
    (300, "202412"),
]


def load_category3_domains(month_id: int) -> set:
    """Load Category 3 domains from CSV."""
    csv_path = ANALYSIS_DIR / f"category3_{month_id}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Category 3 file not found: {csv_path}")

    df = pd.read_csv(csv_path)
    return set(df['domain'].str.lower())


def load_sessions(session_suffix: str) -> pd.DataFrame:
    """Load merged sessions parquet file."""
    session_path = DATA_DIR / "merged_session_files" / f"merged_sessions_{session_suffix}.parquet"
    if not session_path.exists():
        raise FileNotFoundError(f"Session file not found: {session_path}")

    print(f"Loading sessions from: {session_path}")
    df = pd.read_parquet(session_path)
    print(f"  Loaded {len(df):,} sessions")
    return df


def plot_top_category3_sites(cat3_by_site: pd.DataFrame, cat3_minutes: float,
                              cat3_session_count: int, session_suffix: str, top_n: int = 20):
    """
    Create dual-panel horizontal bar chart of top Category 3 sites with "all other" line.
    Similar to the XXX Adult websites chart.
    """
    print(f"  Creating top {top_n} Category 3 sites chart...")

    apply_plot_style()

    # Get top N sites
    top_sites = cat3_by_site.head(top_n).copy()

    # Calculate percentages
    top_sites['session_pct'] = top_sites['sessions'] / cat3_session_count * 100
    top_sites['duration_pct'] = top_sites['total_minutes'] / cat3_minutes * 100

    # Calculate "all other"
    top_sessions = top_sites['sessions'].sum()
    other_sessions = cat3_session_count - top_sessions
    other_session_pct = other_sessions / cat3_session_count * 100

    top_duration = top_sites['total_minutes'].sum()
    other_duration = cat3_minutes - top_duration
    other_duration_pct = other_duration / cat3_minutes * 100

    # Add "all other" row
    other_row = pd.DataFrame([{
        'top_web_name': 'All Other Sites',
        'subcategory': '',
        'sessions': other_sessions,
        'total_minutes': other_duration,
        'session_pct': other_session_pct,
        'duration_pct': other_duration_pct
    }])
    plot_data = pd.concat([top_sites, other_row], ignore_index=True)

    # Create dual-panel figure
    fig, axes = plt.subplots(1, 2, figsize=(14, 9))

    y_pos = range(len(plot_data))
    colors = [UCHICAGO_MAROON] * top_n + ['#767676']  # Gray for "all other"

    # Create labels with ranking numbers and subcategory
    labels = []
    for idx, row in plot_data.iterrows():
        if row['top_web_name'] == 'All Other Sites':
            labels.append(row['top_web_name'])
        else:
            rank = idx + 1
            subcat_short = row['subcategory'][:15] + '...' if len(str(row['subcategory'])) > 15 else row['subcategory']
            labels.append(f"{rank}. {row['top_web_name']}\n    [{subcat_short}]")

    # Left panel: By share of sessions
    ax1 = axes[0]
    ax1.barh(y_pos, plot_data['session_pct'], color=colors)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(labels, fontsize=8)
    ax1.invert_yaxis()
    ax1.set_xlabel('Share of Category 3 Sessions (%)')
    ax1.set_title('By Session Count')

    # Right panel: By share of duration
    ax2 = axes[1]
    ax2.barh(y_pos, plot_data['duration_pct'], color=colors)
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(labels, fontsize=8)
    ax2.invert_yaxis()
    ax2.set_xlabel('Share of Category 3 Hours (%)')
    ax2.set_title('By Time Spent')

    fig.suptitle(f'Top {top_n} Category 3 Sites (Potentially Misclassified Adult Sites)\nMonth: {session_suffix}',
                 fontsize=14, y=1.02)
    plt.tight_layout()

    # Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f'top_category3_sites_{session_suffix}.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  Chart saved to: {output_path}")


def plot_category3_vs_xxx(cat3_by_site: pd.DataFrame, xxx_by_site: pd.DataFrame,
                          xxx_minutes: float, xxx_session_count: int,
                          session_suffix: str, top_n: int = 20):
    """
    Create dual-panel chart comparing top Category 3 sites against XXX Adult traffic.
    Shows Category 3 sites as a percentage of total XXX Adult traffic.
    """
    print(f"  Creating Category 3 vs XXX Adult comparison chart...")

    apply_plot_style()

    # Get top N Category 3 sites
    top_cat3 = cat3_by_site.head(top_n).copy()

    # Calculate percentages relative to XXX Adult totals
    top_cat3['session_pct_of_xxx'] = top_cat3['sessions'] / xxx_session_count * 100
    top_cat3['duration_pct_of_xxx'] = top_cat3['total_minutes'] / xxx_minutes * 100

    # Get top XXX Adult site for reference line
    top_xxx_site = xxx_by_site.iloc[0] if len(xxx_by_site) > 0 else None
    top_xxx_session_pct = top_xxx_site['sessions'] / xxx_session_count * 100 if top_xxx_site is not None else 0
    top_xxx_duration_pct = top_xxx_site['total_minutes'] / xxx_minutes * 100 if top_xxx_site is not None else 0

    # Create dual-panel figure
    fig, axes = plt.subplots(1, 2, figsize=(14, 8))

    y_pos = range(len(top_cat3))

    # Create labels with ranking numbers and subcategory
    labels = []
    for idx, row in top_cat3.iterrows():
        rank = top_cat3.index.get_loc(idx) + 1
        subcat_short = row['subcategory'][:15] + '...' if len(str(row['subcategory'])) > 15 else row['subcategory']
        labels.append(f"{rank}. {row['top_web_name']}\n    [{subcat_short}]")

    # Left panel: By share of XXX Adult sessions
    ax1 = axes[0]
    ax1.barh(y_pos, top_cat3['session_pct_of_xxx'], color=UCHICAGO_MAROON)
    ax1.axvline(x=top_xxx_session_pct, color='#767676', linestyle='--', linewidth=2,
                label=f'Top XXX site ({top_xxx_site["top_web_name"]}): {top_xxx_session_pct:.1f}%')
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(labels, fontsize=8)
    ax1.invert_yaxis()
    ax1.set_xlabel('As % of XXX Adult Sessions')
    ax1.set_title('By Session Count')
    ax1.legend(loc='lower right', fontsize=8)

    # Right panel: By share of XXX Adult duration
    ax2 = axes[1]
    ax2.barh(y_pos, top_cat3['duration_pct_of_xxx'], color=UCHICAGO_MAROON)
    ax2.axvline(x=top_xxx_duration_pct, color='#767676', linestyle='--', linewidth=2,
                label=f'Top XXX site ({top_xxx_site["top_web_name"]}): {top_xxx_duration_pct:.1f}%')
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(labels, fontsize=8)
    ax2.invert_yaxis()
    ax2.set_xlabel('As % of XXX Adult Hours')
    ax2.set_title('By Time Spent')
    ax2.legend(loc='lower right', fontsize=8)

    fig.suptitle(f'Top {top_n} Category 3 Sites Compared to XXX Adult Traffic\nMonth: {session_suffix}',
                 fontsize=14, y=1.02)
    plt.tight_layout()

    # Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f'category3_vs_xxx_{session_suffix}.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  Chart saved to: {output_path}")


def analyze_month(month_id: int, session_suffix: str):
    """Analyze Category 3 traffic for a single month."""

    print(f"\n{'='*70}")
    print(f"MONTH {month_id} (Session file: {session_suffix})")
    print(f"{'='*70}")

    # Load data
    cat3_domains = load_category3_domains(month_id)
    sessions = load_sessions(session_suffix)

    # Normalize web names for matching
    sessions['normalized_name'] = sessions['top_web_name'].str.lower().str.strip()

    # Identify session types
    sessions['is_xxx_adult'] = sessions['subcategory'] == 'XXX Adult'
    sessions['is_cat3'] = sessions['normalized_name'].isin(cat3_domains)

    # Convert duration to minutes
    sessions['duration_minutes'] = sessions['duration'] / 60

    # ===========================================
    # TABLE 1: Traffic Comparison
    # ===========================================
    total_minutes = sessions['duration_minutes'].sum()
    total_sessions = len(sessions)

    xxx_sessions = sessions[sessions['is_xxx_adult']]
    xxx_minutes = xxx_sessions['duration_minutes'].sum()
    xxx_session_count = len(xxx_sessions)

    cat3_sessions = sessions[sessions['is_cat3']]
    cat3_minutes = cat3_sessions['duration_minutes'].sum()
    cat3_session_count = len(cat3_sessions)

    print("\n## Table 1: Traffic Comparison\n")
    print(f"Total sessions: {total_sessions:,} | Total minutes: {total_minutes:,.0f}\n")
    print("| Metric | Category 3 | % of Total | XXX Adult | % of Total | Cat3 as % of XXX |")
    print("|--------|------------|------------|-----------|------------|------------------|")
    print(f"| Sessions | {cat3_session_count:,} | {100*cat3_session_count/total_sessions:.2f}% | {xxx_session_count:,} | {100*xxx_session_count/total_sessions:.2f}% | {100*cat3_session_count/xxx_session_count:.2f}% |")
    print(f"| Minutes | {cat3_minutes:,.0f} | {100*cat3_minutes/total_minutes:.2f}% | {xxx_minutes:,.0f} | {100*xxx_minutes/total_minutes:.2f}% | {100*cat3_minutes/xxx_minutes:.2f}% |")

    # ===========================================
    # TABLE 2: Top Category 3 Sites by Traffic
    # ===========================================
    cat3_by_site = cat3_sessions.groupby(['top_web_name', 'subcategory']).agg(
        sessions=('duration', 'size'),
        total_minutes=('duration_minutes', 'sum'),
        unique_persons=('person_id', 'nunique')
    ).reset_index()
    cat3_by_site = cat3_by_site.sort_values('total_minutes', ascending=False)

    print("\n## Table 2: Top 20 Category 3 Sites by Time Spent\n")
    print("| Rank | Site | Comscore Subcategory | Sessions | % of XXX | Minutes | % of XXX | Unique Persons |")
    print("|------|------|---------------------|----------|----------|---------|----------|----------------|")
    for i, row in cat3_by_site.head(20).iterrows():
        rank = cat3_by_site.index.get_loc(i) + 1
        sess_pct = 100 * row['sessions'] / xxx_session_count
        min_pct = 100 * row['total_minutes'] / xxx_minutes
        print(f"| {rank} | {row['top_web_name']} | {row['subcategory']} | {row['sessions']:,} | {sess_pct:.2f}% | {row['total_minutes']:,.0f} | {min_pct:.2f}% | {row['unique_persons']:,} |")

    # ===========================================
    # Create Chart for Top Category 3 Sites
    # ===========================================
    plot_top_category3_sites(cat3_by_site, cat3_minutes, cat3_session_count, session_suffix)

    # ===========================================
    # TABLE 5: Comparison with Top XXX Adult Sites
    # ===========================================
    xxx_by_site = xxx_sessions.groupby('top_web_name').agg(
        sessions=('duration', 'size'),
        total_minutes=('duration_minutes', 'sum')
    ).reset_index()
    xxx_by_site = xxx_by_site.sort_values('total_minutes', ascending=False)

    # ===========================================
    # Create Chart Comparing Category 3 to XXX Adult
    # ===========================================
    plot_category3_vs_xxx(cat3_by_site, xxx_by_site, xxx_minutes, xxx_session_count, session_suffix)

    # Get the traffic of top XXX Adult sites for comparison
    top_xxx_site = xxx_by_site.iloc[0] if len(xxx_by_site) > 0 else None
    top_10_xxx_minutes = xxx_by_site.head(10)['total_minutes'].sum()
    top_50_xxx_minutes = xxx_by_site.head(50)['total_minutes'].sum()

    print("\n## Table 3: Category 3 Traffic in Context\n")
    print("| Comparison | Minutes |")
    print("|------------|---------|")
    print(f"| Total Category 3 traffic | {cat3_minutes:,.0f} |")
    if top_xxx_site is not None:
        print(f"| Top 1 XXX Adult site ({top_xxx_site['top_web_name']}) | {top_xxx_site['total_minutes']:,.0f} |")
    print(f"| Top 10 XXX Adult sites combined | {top_10_xxx_minutes:,.0f} |")
    print(f"| Top 50 XXX Adult sites combined | {top_50_xxx_minutes:,.0f} |")

    # Where does total Cat3 traffic rank?
    cat3_rank = (xxx_by_site['total_minutes'] > cat3_minutes).sum() + 1
    print(f"\nCategory 3 total traffic would rank #{cat3_rank} if it were a single XXX Adult site.")

    return {
        'month_id': month_id,
        'xxx_minutes': xxx_minutes,
        'cat3_minutes': cat3_minutes,
        'cat3_pct_of_xxx': 100 * cat3_minutes / xxx_minutes if xxx_minutes > 0 else 0,
        'cat3_sessions': cat3_session_count,
        'xxx_sessions': xxx_session_count,
    }


def main():
    print("=" * 70)
    print("CATEGORY 3 TRAFFIC ANALYSIS")
    print("Comparing traffic on potentially misclassified sites vs XXX Adult")
    print("=" * 70)

    results = []
    for month_id, session_suffix in MONTHS:
        try:
            result = analyze_month(month_id, session_suffix)
            results.append(result)
        except FileNotFoundError as e:
            print(f"\nSkipping month {month_id}: {e}")

    # Summary comparison across months
    if len(results) > 1:
        print("\n" + "=" * 70)
        print("CROSS-MONTH SUMMARY")
        print("=" * 70)
        print("\n| Month | XXX Adult Minutes | Cat3 Minutes | Cat3 as % of XXX |")
        print("|-------|-------------------|--------------|------------------|")
        for r in results:
            print(f"| {r['month_id']} | {r['xxx_minutes']:,.0f} | {r['cat3_minutes']:,.0f} | {r['cat3_pct_of_xxx']:.2f}% |")

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
