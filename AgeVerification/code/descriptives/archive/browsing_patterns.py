"""
Analyze browsing patterns for XXX Adult content.

Author: mattbrownecon, assisted by Claude
Date created: 2026-01-23
Last updated: 2026-01-23
Purpose: Generate time-of-day patterns and session journey visualizations for XXX Adult.

Outputs:
    - output/descriptives/xxx_time_patterns_202201.png
    - output/descriptives/xxx_session_journeys_202201.png
    - output/descriptives/xxx_hourly_pattern_202201.csv
    - output/descriptives/xxx_daily_pattern_202201.csv
    - output/descriptives/xxx_session_journeys_202201.csv
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import logging
import sys

# Add code directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from plot_style import apply_plot_style, UCHICAGO_MAROON, COLOR_PALETTE

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path.cwd()
DATA_DIR = BASE_DIR / 'data' / 'ProcessComscore' / 'merged_session_files'
OUTPUT_DIR = BASE_DIR / 'output' / 'descriptives'

# Constants
MONTH = '202201'


def load_session_data(columns=None):
    """Load merged session data."""
    path = DATA_DIR / f'merged_sessions_{MONTH}.parquet'
    logger.info(f"Loading {path}...")
    return pd.read_parquet(path, columns=columns)


def is_xxx_adult(df):
    """Return boolean mask for XXX Adult sessions."""
    return (df['category'] == 'XXX Adult') | (df['subcategory'] == 'XXX Adult')


def analyze_time_patterns(df):
    """
    Analyze when people visit XXX Adult sites.

    Returns hourly and day-of-week DataFrames.
    """
    logger.info("Analyzing time patterns...")

    # Convert first_ss2k to datetime components
    df['datetime'] = pd.to_datetime(df['first_ss2k'], unit='s', origin='2000-01-01')
    df['hour'] = df['datetime'].dt.hour
    df['day_of_week'] = df['datetime'].dt.dayofweek  # 0=Monday, 6=Sunday

    # Flag XXX Adult
    df['is_xxx'] = is_xxx_adult(df)

    # Hourly pattern
    hourly_all = df.groupby('hour').size()
    hourly_xxx = df[df['is_xxx']].groupby('hour').size()

    hourly_df = pd.DataFrame({
        'all_sessions': hourly_all,
        'xxx_sessions': hourly_xxx
    }).fillna(0)
    hourly_df['all_pct'] = hourly_df['all_sessions'] / hourly_df['all_sessions'].sum() * 100
    hourly_df['xxx_pct'] = hourly_df['xxx_sessions'] / hourly_df['xxx_sessions'].sum() * 100
    hourly_df['xxx_share_of_hour'] = hourly_df['xxx_sessions'] / hourly_df['all_sessions'] * 100

    # Day of week pattern
    dow_all = df.groupby('day_of_week').size()
    dow_xxx = df[df['is_xxx']].groupby('day_of_week').size()

    dow_df = pd.DataFrame({
        'all_sessions': dow_all,
        'xxx_sessions': dow_xxx
    }).fillna(0)
    dow_df.index = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    dow_df['all_pct'] = dow_df['all_sessions'] / dow_df['all_sessions'].sum() * 100
    dow_df['xxx_pct'] = dow_df['xxx_sessions'] / dow_df['xxx_sessions'].sum() * 100

    return hourly_df, dow_df


def plot_time_patterns(hourly_df, dow_df):
    """Create time patterns visualization."""
    logger.info("Creating time patterns plot...")

    apply_plot_style()

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    # Colors from palette
    color_all = COLOR_PALETTE[2]   # Blue
    color_xxx = UCHICAGO_MAROON    # Maroon

    # Panel 1: Hourly distribution
    ax = axes[0]
    x = hourly_df.index
    width = 0.35
    ax.bar(x - width/2, hourly_df['all_pct'], width, label='All Traffic', color=color_all, alpha=0.8)
    ax.bar(x + width/2, hourly_df['xxx_pct'], width, label='XXX Adult', color=color_xxx, alpha=0.8)
    ax.set_xlabel('Hour of Day')
    ax.set_ylabel('% of Sessions')
    ax.set_title('Hourly Distribution')
    ax.legend(loc='upper right')
    ax.set_xticks(range(0, 24, 3))

    # Panel 2: Day of week
    ax = axes[1]
    x = np.arange(len(dow_df))
    ax.bar(x - width/2, dow_df['all_pct'], width, label='All Traffic', color=color_all, alpha=0.8)
    ax.bar(x + width/2, dow_df['xxx_pct'], width, label='XXX Adult', color=color_xxx, alpha=0.8)
    ax.set_xlabel('Day of Week')
    ax.set_ylabel('% of Sessions')
    ax.set_title('Day of Week Distribution')
    ax.set_xticks(x)
    ax.set_xticklabels(dow_df.index)
    ax.legend(loc='upper right')

    # Panel 3: XXX share by hour
    ax = axes[2]
    ax.plot(hourly_df.index, hourly_df['xxx_share_of_hour'], marker='o', color=color_xxx, linewidth=2)
    daily_avg = hourly_df['xxx_sessions'].sum() / hourly_df['all_sessions'].sum() * 100
    ax.axhline(y=daily_avg, color='gray', linestyle='--', label=f'Daily Average ({daily_avg:.1f}%)')
    ax.set_xlabel('Hour of Day')
    ax.set_ylabel('XXX Adult as % of All Sessions')
    ax.set_title('XXX Adult Share by Hour')
    ax.set_xticks(range(0, 24, 3))
    ax.legend(loc='upper right')

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / f'xxx_time_patterns_{MONTH}.png', dpi=300, bbox_inches='tight')
    plt.close()

    logger.info(f"Saved time patterns plot")


def analyze_session_journeys(df):
    """
    Analyze what people browse before and after XXX Adult sessions.

    Returns DataFrame with journey statistics.
    """
    logger.info("Analyzing session journeys...")

    df['is_xxx'] = is_xxx_adult(df)

    # Sort by machine and time
    df = df.sort_values(['machine_id', 'first_ss2k'])

    # Get previous and next websites
    df['prev_website'] = df.groupby('machine_id')['top_web_name'].shift(1)
    df['next_website'] = df.groupby('machine_id')['top_web_name'].shift(-1)
    df['prev_is_xxx'] = df.groupby('machine_id')['is_xxx'].shift(1)
    df['next_is_xxx'] = df.groupby('machine_id')['is_xxx'].shift(-1)

    # Time gap to previous/next session (in minutes)
    df['prev_time'] = df.groupby('machine_id')['first_ss2k'].shift(1)
    df['next_time'] = df.groupby('machine_id')['first_ss2k'].shift(-1)
    df['time_from_prev'] = (df['first_ss2k'] - df['prev_time']) / 60
    df['time_to_next'] = (df['next_time'] - df['first_ss2k']) / 60

    # Filter to XXX Adult sessions with adjacent sessions within 30 minutes
    xxx_sessions = df[df['is_xxx']].copy()
    before_xxx = xxx_sessions[xxx_sessions['time_from_prev'] <= 30].copy()
    after_xxx = xxx_sessions[xxx_sessions['time_to_next'] <= 30].copy()

    # Count what comes before/after
    before_sites = before_xxx['prev_website'].value_counts().head(20)
    after_sites = after_xxx['next_website'].value_counts().head(20)

    # Calculate XXX->XXX transitions
    xxx_to_xxx = after_xxx['next_is_xxx'].sum()
    xxx_to_other = (~after_xxx['next_is_xxx']).sum()
    xxx_from_xxx = before_xxx['prev_is_xxx'].sum()
    xxx_from_other = (~before_xxx['prev_is_xxx']).sum()

    journey_stats = {
        'xxx_sessions_with_prior': len(before_xxx),
        'xxx_sessions_with_next': len(after_xxx),
        'xxx_from_xxx': int(xxx_from_xxx),
        'xxx_from_other': int(xxx_from_other),
        'xxx_to_xxx': int(xxx_to_xxx),
        'xxx_to_other': int(xxx_to_other),
        'pct_from_xxx': xxx_from_xxx / len(before_xxx) * 100,
        'pct_to_xxx': xxx_to_xxx / len(after_xxx) * 100,
    }

    # Create journey DataFrame
    journey_df = pd.DataFrame({
        'before_website': before_sites.index.tolist(),
        'before_count': before_sites.values.tolist(),
        'after_website': after_sites.index.tolist(),
        'after_count': after_sites.values.tolist(),
    })

    logger.info(f"  XXX sessions with prior session (within 30min): {len(before_xxx):,}")
    logger.info(f"  XXX sessions with next session (within 30min): {len(after_xxx):,}")
    logger.info(f"  % coming FROM another XXX site: {journey_stats['pct_from_xxx']:.1f}%")
    logger.info(f"  % going TO another XXX site: {journey_stats['pct_to_xxx']:.1f}%")

    return journey_df, journey_stats, before_sites, after_sites


def plot_session_journeys(journey_stats, before_sites, after_sites):
    """Create session journeys visualization."""
    logger.info("Creating session journeys plot...")

    apply_plot_style()

    fig, axes = plt.subplots(1, 3, figsize=(18, 7))

    # Panel 1: Top sites BEFORE XXX
    ax = axes[0]
    top_before = before_sites.head(12)
    y = range(len(top_before))
    colors = [UCHICAGO_MAROON if 'XXX' in str(site) or site in [
        'CHATURBATE.COM', 'PORNHUB.COM', 'XHAMSTER.COM', 'XVIDEOS.COM',
        'XNXX.COM', 'LIVEJASMIN.COM', 'SPANKBANG.COM', 'STRIPCHAT.COM',
        'FAPHOUSE.COM', 'RULE34.XXX', 'CAMSCHAT.NET', 'BONGACAMS.COM'
    ] else COLOR_PALETTE[2] for site in top_before.index]

    bars = ax.barh(y, top_before.values, color=colors, alpha=0.85)
    ax.set_yticks(y)
    ax.set_yticklabels(top_before.index)
    ax.set_xlabel('Number of Sessions')
    ax.set_title('Where Users Come From\n(Session Before XXX Adult)')
    ax.invert_yaxis()

    # Add count labels
    for i, (count, site) in enumerate(zip(top_before.values, top_before.index)):
        ax.text(count + 1000, i, f'{count:,}', va='center', fontsize=9)

    # Panel 2: Top sites AFTER XXX
    ax = axes[1]
    top_after = after_sites.head(12)
    y = range(len(top_after))
    colors = [UCHICAGO_MAROON if 'XXX' in str(site) or site in [
        'CHATURBATE.COM', 'PORNHUB.COM', 'XHAMSTER.COM', 'XVIDEOS.COM',
        'XNXX.COM', 'LIVEJASMIN.COM', 'SPANKBANG.COM', 'STRIPCHAT.COM',
        'FAPHOUSE.COM', 'RULE34.XXX', 'CAMSCHAT.NET', 'BONGACAMS.COM',
        'XHAMSTERLIVE.COM', 'BANGCREATIVES.COM', 'JERKMATE.COM'
    ] else COLOR_PALETTE[2] for site in top_after.index]

    bars = ax.barh(y, top_after.values, color=colors, alpha=0.85)
    ax.set_yticks(y)
    ax.set_yticklabels(top_after.index)
    ax.set_xlabel('Number of Sessions')
    ax.set_title('Where Users Go Next\n(Session After XXX Adult)')
    ax.invert_yaxis()

    for i, (count, site) in enumerate(zip(top_after.values, top_after.index)):
        ax.text(count + 1000, i, f'{count:,}', va='center', fontsize=9)

    # Panel 3: XXX to XXX flow summary
    ax = axes[2]

    # Create stacked bar for before/after
    categories = ['Coming From', 'Going To']
    xxx_vals = [journey_stats['pct_from_xxx'], journey_stats['pct_to_xxx']]
    other_vals = [100 - journey_stats['pct_from_xxx'], 100 - journey_stats['pct_to_xxx']]

    x = np.arange(len(categories))
    width = 0.5

    bars1 = ax.bar(x, xxx_vals, width, label='Another XXX Site', color=UCHICAGO_MAROON, alpha=0.85)
    bars2 = ax.bar(x, other_vals, width, bottom=xxx_vals, label='Non-XXX Site', color=COLOR_PALETTE[2], alpha=0.85)

    ax.set_ylabel('% of Sessions')
    ax.set_title('XXX-to-XXX Transitions')
    ax.set_xticks(x)
    ax.set_xticklabels(categories)
    ax.legend(loc='upper right')
    ax.set_ylim(0, 100)

    # Add percentage labels
    for i, (xxx_pct, other_pct) in enumerate(zip(xxx_vals, other_vals)):
        ax.text(i, xxx_pct/2, f'{xxx_pct:.1f}%', ha='center', va='center', color='white', fontweight='bold', fontsize=12)
        ax.text(i, xxx_pct + other_pct/2, f'{other_pct:.1f}%', ha='center', va='center', color='white', fontweight='bold', fontsize=12)

    # Add legend for bar colors
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=UCHICAGO_MAROON, alpha=0.85, label='XXX Adult Site'),
        Patch(facecolor=COLOR_PALETTE[2], alpha=0.85, label='Non-XXX Site')
    ]
    axes[0].legend(handles=legend_elements, loc='lower right', fontsize=10)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / f'xxx_session_journeys_{MONTH}.png', dpi=300, bbox_inches='tight')
    plt.close()

    logger.info(f"Saved session journeys plot")


def main():
    """Run all analyses."""
    logger.info("Starting browsing pattern analyses...")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load data for time patterns
    df_time = load_session_data(columns=['first_ss2k', 'category', 'subcategory', 'session_id'])
    hourly_df, dow_df = analyze_time_patterns(df_time)

    # Save CSVs
    hourly_df.to_csv(OUTPUT_DIR / f'xxx_hourly_pattern_{MONTH}.csv')
    dow_df.to_csv(OUTPUT_DIR / f'xxx_daily_pattern_{MONTH}.csv')

    # Plot time patterns
    plot_time_patterns(hourly_df, dow_df)

    # Free memory
    del df_time

    # Load data for session journeys
    df_journey = load_session_data(columns=['machine_id', 'first_ss2k', 'category', 'subcategory', 'top_web_name'])
    journey_df, journey_stats, before_sites, after_sites = analyze_session_journeys(df_journey)

    # Save CSV
    journey_df.to_csv(OUTPUT_DIR / f'xxx_session_journeys_{MONTH}.csv', index=False)

    # Plot session journeys
    plot_session_journeys(journey_stats, before_sites, after_sites)

    logger.info("All analyses complete!")
    logger.info(f"Outputs saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
