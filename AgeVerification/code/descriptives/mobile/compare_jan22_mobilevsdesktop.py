"""
Compare Mobile vs Desktop XXX Adult Browsing: January 2022

Side-by-side comparison of XXX Adult browsing patterns across platforms:
1. Share of all sessions that are to XXX Adult websites
2. Minutes per machine spent on XXX Adult websites
3. Top adult websites by sessions and by minutes

Usage:
    python code/descriptives/mobile/compare_jan22_mobilevsdesktop.py

Outputs:
    - output/descriptives/mobile/compare_xxx_summary_202201.csv
    - output/descriptives/mobile/compare_xxx_minutes_per_machine_202201.csv
    - output/descriptives/mobile/compare_xxx_top_sites_by_sessions_202201.csv
    - output/descriptives/mobile/compare_xxx_top_sites_by_minutes_202201.csv
"""

import pandas as pd
import numpy as np
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
DATA_DIR = BASE_DIR / 'data' / 'ProcessComscore' / 'merged_session_files'
OUTPUT_DIR = BASE_DIR / 'output' / 'descriptives' / 'mobile'

MONTH_ID = '202201'


def load_data():
    """Load both mobile and desktop merged session files."""
    mobile_path = DATA_DIR / f'merged_mobile_sessions_{MONTH_ID}.parquet'
    desktop_path = DATA_DIR / f'merged_sessions_{MONTH_ID}.parquet'

    logger.info("Loading mobile sessions...")
    mobile = pd.read_parquet(mobile_path)
    mobile['machine_id'] = mobile['machine_id'].astype(str)
    logger.info(f"  Mobile: {len(mobile):,} sessions, {mobile['machine_id'].nunique():,} machines")

    logger.info("Loading desktop sessions...")
    desktop = pd.read_parquet(desktop_path)
    desktop['machine_id'] = desktop['machine_id'].astype(str)
    logger.info(f"  Desktop: {len(desktop):,} sessions, {desktop['machine_id'].nunique():,} machines")

    return mobile, desktop


def compute_xxx_session_share(df, platform_label):
    """Compute XXX Adult session share for one platform."""
    total_sessions = len(df)
    total_machines = df['machine_id'].nunique()

    xxx = df[df['subcategory'] == 'XXX Adult']
    xxx_sessions = len(xxx)
    xxx_machines = xxx['machine_id'].nunique()

    return {
        'platform': platform_label,
        'total_sessions': total_sessions,
        'total_machines': total_machines,
        'xxx_sessions': xxx_sessions,
        'xxx_machines': xxx_machines,
        'xxx_session_share': xxx_sessions / total_sessions,
        'xxx_machine_share': xxx_machines / total_machines,
        'xxx_sessions_per_xxx_machine': xxx_sessions / xxx_machines if xxx_machines > 0 else 0,
    }


def compute_xxx_minutes_per_machine(df, platform_label):
    """Compute distribution of XXX Adult minutes per machine for one platform."""
    xxx = df[df['subcategory'] == 'XXX Adult'].copy()
    xxx['duration_min'] = xxx['duration'] / 60

    device_minutes = xxx.groupby('machine_id').agg(
        total_minutes=('duration_min', 'sum'),
        total_sessions=('session_id' if 'session_id' in xxx.columns else 'machine_id', 'count'),
        avg_minutes_per_session=('duration_min', 'mean'),
    ).reset_index()

    return {
        'platform': platform_label,
        'machines_with_xxx': len(device_minutes),
        'mean_total_minutes': device_minutes['total_minutes'].mean(),
        'median_total_minutes': device_minutes['total_minutes'].median(),
        'p25_total_minutes': device_minutes['total_minutes'].quantile(0.25),
        'p75_total_minutes': device_minutes['total_minutes'].quantile(0.75),
        'p95_total_minutes': device_minutes['total_minutes'].quantile(0.95),
        'max_total_minutes': device_minutes['total_minutes'].max(),
        'mean_sessions_per_machine': device_minutes['total_sessions'].mean(),
        'median_sessions_per_machine': device_minutes['total_sessions'].median(),
        'mean_minutes_per_session': device_minutes['avg_minutes_per_session'].mean(),
        'median_minutes_per_session': device_minutes['avg_minutes_per_session'].median(),
    }


def compute_top_xxx_sites(df, platform_label, top_n=25):
    """Compute top XXX Adult websites by sessions and minutes for one platform."""
    xxx = df[df['subcategory'] == 'XXX Adult'].copy()
    xxx['duration_min'] = xxx['duration'] / 60

    total_xxx_sessions = len(xxx)
    total_xxx_minutes = xxx['duration_min'].sum()

    # By sessions
    by_sessions = xxx.groupby('top_web_name').agg(
        sessions=('machine_id', 'count'),
        unique_machines=('machine_id', 'nunique'),
    ).sort_values('sessions', ascending=False).head(top_n).reset_index()

    by_sessions['platform'] = platform_label
    by_sessions['session_share'] = by_sessions['sessions'] / total_xxx_sessions
    by_sessions['cumulative_session_share'] = by_sessions['session_share'].cumsum()

    # By minutes
    by_minutes = xxx.groupby('top_web_name').agg(
        total_minutes=('duration_min', 'sum'),
        sessions=('machine_id', 'count'),
        unique_machines=('machine_id', 'nunique'),
        avg_minutes_per_session=('duration_min', 'mean'),
    ).sort_values('total_minutes', ascending=False).head(top_n).reset_index()

    by_minutes['platform'] = platform_label
    by_minutes['minute_share'] = by_minutes['total_minutes'] / total_xxx_minutes
    by_minutes['cumulative_minute_share'] = by_minutes['minute_share'].cumsum()

    return by_sessions, by_minutes


def print_comparison_table(mobile_stats, desktop_stats, metrics, labels=None):
    """Print a formatted comparison table to the log."""
    if labels is None:
        labels = {m: m for m in metrics}

    max_label_len = max(len(labels.get(m, m)) for m in metrics)

    for m in metrics:
        label = labels.get(m, m)
        mv = mobile_stats[m]
        dv = desktop_stats[m]

        if isinstance(mv, float) and mv < 1 and m.endswith('share'):
            logger.info(f"  {label:<{max_label_len}}  Mobile: {mv*100:>8.2f}%    Desktop: {dv*100:>8.2f}%")
        elif isinstance(mv, float):
            logger.info(f"  {label:<{max_label_len}}  Mobile: {mv:>12.1f}    Desktop: {dv:>12.1f}")
        else:
            logger.info(f"  {label:<{max_label_len}}  Mobile: {mv:>12,}    Desktop: {dv:>12,}")


def main():
    logger.info("=" * 70)
    logger.info("MOBILE vs DESKTOP XXX ADULT COMPARISON: January 2022")
    logger.info("=" * 70)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load data
    mobile, desktop = load_data()

    # ---- 1. Session Share ----
    logger.info("\n" + "-" * 70)
    logger.info("1. XXX ADULT SESSION SHARE")
    logger.info("-" * 70)

    mobile_share = compute_xxx_session_share(mobile, 'mobile')
    desktop_share = compute_xxx_session_share(desktop, 'desktop')

    print_comparison_table(mobile_share, desktop_share,
        ['total_sessions', 'total_machines', 'xxx_sessions', 'xxx_machines',
         'xxx_session_share', 'xxx_machine_share', 'xxx_sessions_per_xxx_machine'],
        labels={
            'total_sessions': 'Total sessions',
            'total_machines': 'Total machines',
            'xxx_sessions': 'XXX Adult sessions',
            'xxx_machines': 'Machines visiting XXX',
            'xxx_session_share': 'XXX session share',
            'xxx_machine_share': 'XXX machine share',
            'xxx_sessions_per_xxx_machine': 'XXX sessions per XXX machine',
        })

    summary_df = pd.DataFrame([mobile_share, desktop_share])
    summary_df.to_csv(OUTPUT_DIR / f'compare_xxx_summary_{MONTH_ID}.csv', index=False)

    # ---- 2. Minutes Per Machine ----
    logger.info("\n" + "-" * 70)
    logger.info("2. XXX ADULT MINUTES PER MACHINE (among machines that visit)")
    logger.info("-" * 70)

    mobile_mins = compute_xxx_minutes_per_machine(mobile, 'mobile')
    desktop_mins = compute_xxx_minutes_per_machine(desktop, 'desktop')

    print_comparison_table(mobile_mins, desktop_mins,
        ['machines_with_xxx', 'mean_total_minutes', 'median_total_minutes',
         'p25_total_minutes', 'p75_total_minutes', 'p95_total_minutes',
         'mean_sessions_per_machine', 'median_sessions_per_machine',
         'mean_minutes_per_session', 'median_minutes_per_session'],
        labels={
            'machines_with_xxx': 'Machines with XXX',
            'mean_total_minutes': 'Mean total min/machine',
            'median_total_minutes': 'Median total min/machine',
            'p25_total_minutes': 'p25 total min/machine',
            'p75_total_minutes': 'p75 total min/machine',
            'p95_total_minutes': 'p95 total min/machine',
            'mean_sessions_per_machine': 'Mean sessions/machine',
            'median_sessions_per_machine': 'Median sessions/machine',
            'mean_minutes_per_session': 'Mean min/session',
            'median_minutes_per_session': 'Median min/session',
        })

    minutes_df = pd.DataFrame([mobile_mins, desktop_mins])
    minutes_df.to_csv(OUTPUT_DIR / f'compare_xxx_minutes_per_machine_{MONTH_ID}.csv', index=False)

    # ---- 3. Top Sites ----
    logger.info("\n" + "-" * 70)
    logger.info("3. TOP XXX ADULT WEBSITES BY SESSIONS")
    logger.info("-" * 70)

    mob_by_sess, mob_by_min = compute_top_xxx_sites(mobile, 'mobile')
    desk_by_sess, desk_by_min = compute_top_xxx_sites(desktop, 'desktop')

    logger.info(f"\n  {'Rank':<5} {'Mobile':<30} {'Share':>7}    {'Desktop':<30} {'Share':>7}")
    logger.info(f"  {'-'*5} {'-'*30} {'-'*7}    {'-'*30} {'-'*7}")
    for i in range(min(15, len(mob_by_sess), len(desk_by_sess))):
        mr = mob_by_sess.iloc[i]
        dr = desk_by_sess.iloc[i]
        logger.info(f"  {i+1:<5} {mr['top_web_name']:<30} {mr['session_share']*100:>6.1f}%    {dr['top_web_name']:<30} {dr['session_share']*100:>6.1f}%")

    by_sessions_df = pd.concat([mob_by_sess, desk_by_sess], ignore_index=True)
    by_sessions_df.to_csv(OUTPUT_DIR / f'compare_xxx_top_sites_by_sessions_{MONTH_ID}.csv', index=False)

    logger.info("\n" + "-" * 70)
    logger.info("4. TOP XXX ADULT WEBSITES BY MINUTES")
    logger.info("-" * 70)

    logger.info(f"\n  {'Rank':<5} {'Mobile':<30} {'Share':>7}    {'Desktop':<30} {'Share':>7}")
    logger.info(f"  {'-'*5} {'-'*30} {'-'*7}    {'-'*30} {'-'*7}")
    for i in range(min(15, len(mob_by_min), len(desk_by_min))):
        mr = mob_by_min.iloc[i]
        dr = desk_by_min.iloc[i]
        logger.info(f"  {i+1:<5} {mr['top_web_name']:<30} {mr['minute_share']*100:>6.1f}%    {dr['top_web_name']:<30} {dr['minute_share']*100:>6.1f}%")

    by_minutes_df = pd.concat([mob_by_min, desk_by_min], ignore_index=True)
    by_minutes_df.to_csv(OUTPUT_DIR / f'compare_xxx_top_sites_by_minutes_{MONTH_ID}.csv', index=False)

    # Done
    logger.info("\n" + "=" * 70)
    logger.info("COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Output saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
