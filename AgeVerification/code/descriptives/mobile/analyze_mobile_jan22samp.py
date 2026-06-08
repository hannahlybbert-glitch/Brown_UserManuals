"""
Mobile Data Exploration: January 2022 Sample

Summary statistics on XXX Adult browsing in the merged mobile sessions data:
1. Share of all sessions that are to XXX Adult websites
2. Minutes per device spent on XXX Adult websites
3. Top adult websites by sessions and by minutes

Usage:
    python code/descriptives/mobile/analyze_mobile_jan22samp.py

Outputs:
    - output/descriptives/mobile/mobile_xxx_summary_202201.csv
    - output/descriptives/mobile/mobile_xxx_minutes_per_device_202201.csv
    - output/descriptives/mobile/mobile_xxx_top_sites_by_sessions_202201.csv
    - output/descriptives/mobile/mobile_xxx_top_sites_by_minutes_202201.csv
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


def load_mobile_sessions(month_id):
    """Load merged mobile sessions parquet file."""
    file_path = DATA_DIR / f'merged_mobile_sessions_{month_id}.parquet'

    if not file_path.exists():
        raise FileNotFoundError(f"Merged mobile sessions file not found: {file_path}")

    logger.info(f"Loading merged mobile sessions for {month_id}...")
    df = pd.read_parquet(file_path)

    # Ensure IDs are strings
    for col in ['machine_id', 'pattern_id']:
        if col in df.columns:
            df[col] = df[col].astype(str)

    logger.info(f"  Loaded {len(df):,} sessions from {df['machine_id'].nunique():,} devices")
    return df


def compute_xxx_session_share(df):
    """Compute share of sessions going to XXX Adult websites."""
    logger.info("Computing XXX Adult session shares...")

    total_sessions = len(df)
    total_devices = df['machine_id'].nunique()

    xxx = df[df['subcategory'] == 'XXX Adult']
    xxx_sessions = len(xxx)
    xxx_devices = xxx['machine_id'].nunique()

    summary = pd.DataFrame([
        {'metric': 'total_sessions', 'value': total_sessions},
        {'metric': 'total_devices', 'value': total_devices},
        {'metric': 'xxx_sessions', 'value': xxx_sessions},
        {'metric': 'xxx_devices', 'value': xxx_devices},
        {'metric': 'xxx_session_share', 'value': xxx_sessions / total_sessions},
        {'metric': 'xxx_device_share', 'value': xxx_devices / total_devices},
        {'metric': 'xxx_sessions_per_xxx_device', 'value': xxx_sessions / xxx_devices if xxx_devices > 0 else 0},
    ])

    logger.info(f"  Total sessions: {total_sessions:,}")
    logger.info(f"  XXX Adult sessions: {xxx_sessions:,} ({xxx_sessions/total_sessions*100:.2f}%)")
    logger.info(f"  Devices visiting XXX Adult: {xxx_devices:,} / {total_devices:,} ({xxx_devices/total_devices*100:.2f}%)")
    logger.info(f"  XXX sessions per XXX device: {xxx_sessions/xxx_devices:.1f}")

    return summary


def compute_xxx_minutes_per_device(df):
    """Compute minutes per device spent on XXX Adult websites."""
    logger.info("Computing XXX Adult minutes per device...")

    # Duration is in seconds; convert to minutes
    xxx = df[df['subcategory'] == 'XXX Adult'].copy()
    xxx['duration_min'] = xxx['duration'] / 60

    # Per-device statistics
    device_minutes = xxx.groupby('machine_id').agg(
        total_minutes=('duration_min', 'sum'),
        total_sessions=('session_id', 'count'),
        avg_session_minutes=('duration_min', 'mean'),
    ).reset_index()

    # Summary distribution
    stats = pd.DataFrame([
        {'metric': 'devices_with_xxx', 'value': len(device_minutes)},
        {'metric': 'mean_total_minutes', 'value': device_minutes['total_minutes'].mean()},
        {'metric': 'median_total_minutes', 'value': device_minutes['total_minutes'].median()},
        {'metric': 'p25_total_minutes', 'value': device_minutes['total_minutes'].quantile(0.25)},
        {'metric': 'p75_total_minutes', 'value': device_minutes['total_minutes'].quantile(0.75)},
        {'metric': 'p95_total_minutes', 'value': device_minutes['total_minutes'].quantile(0.95)},
        {'metric': 'max_total_minutes', 'value': device_minutes['total_minutes'].max()},
        {'metric': 'mean_sessions_per_device', 'value': device_minutes['total_sessions'].mean()},
        {'metric': 'median_sessions_per_device', 'value': device_minutes['total_sessions'].median()},
        {'metric': 'mean_minutes_per_session', 'value': device_minutes['avg_session_minutes'].mean()},
        {'metric': 'median_minutes_per_session', 'value': device_minutes['avg_session_minutes'].median()},
    ])

    logger.info(f"  Devices with XXX Adult: {len(device_minutes):,}")
    logger.info(f"  Mean total minutes per device: {device_minutes['total_minutes'].mean():.1f}")
    logger.info(f"  Median total minutes per device: {device_minutes['total_minutes'].median():.1f}")
    logger.info(f"  Mean minutes per session: {device_minutes['avg_session_minutes'].mean():.1f}")
    logger.info(f"  Median minutes per session: {device_minutes['avg_session_minutes'].median():.1f}")

    return stats


def compute_top_xxx_sites(df, top_n=25):
    """Compute top XXX Adult websites by sessions and by total minutes."""
    logger.info(f"Computing top {top_n} XXX Adult websites...")

    xxx = df[df['subcategory'] == 'XXX Adult'].copy()
    xxx['duration_min'] = xxx['duration'] / 60

    # By sessions
    by_sessions = xxx.groupby('top_web_name').agg(
        sessions=('session_id', 'count'),
        unique_devices=('machine_id', 'nunique'),
    ).sort_values('sessions', ascending=False).head(top_n).reset_index()

    by_sessions['session_share'] = by_sessions['sessions'] / len(xxx)
    by_sessions['cumulative_session_share'] = by_sessions['session_share'].cumsum()

    logger.info(f"  Top 5 by sessions:")
    for _, row in by_sessions.head(5).iterrows():
        logger.info(f"    {row['top_web_name']}: {row['sessions']:,} sessions ({row['session_share']*100:.1f}%)")

    # By total minutes
    by_minutes = xxx.groupby('top_web_name').agg(
        total_minutes=('duration_min', 'sum'),
        sessions=('session_id', 'count'),
        unique_devices=('machine_id', 'nunique'),
        avg_minutes_per_session=('duration_min', 'mean'),
    ).sort_values('total_minutes', ascending=False).head(top_n).reset_index()

    total_xxx_minutes = xxx['duration_min'].sum()
    by_minutes['minute_share'] = by_minutes['total_minutes'] / total_xxx_minutes
    by_minutes['cumulative_minute_share'] = by_minutes['minute_share'].cumsum()

    logger.info(f"  Top 5 by minutes:")
    for _, row in by_minutes.head(5).iterrows():
        logger.info(f"    {row['top_web_name']}: {row['total_minutes']:,.0f} min ({row['minute_share']*100:.1f}%)")

    return by_sessions, by_minutes


def main():
    logger.info("=" * 70)
    logger.info("MOBILE XXX ADULT EXPLORATION: January 2022")
    logger.info("=" * 70)

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load data
    df = load_mobile_sessions(MONTH_ID)

    # 1. Session share
    logger.info("\n" + "-" * 70)
    logger.info("1. XXX ADULT SESSION SHARE")
    logger.info("-" * 70)
    session_share = compute_xxx_session_share(df)
    session_share.to_csv(OUTPUT_DIR / f'mobile_xxx_summary_{MONTH_ID}.csv', index=False)

    # 2. Minutes per device
    logger.info("\n" + "-" * 70)
    logger.info("2. XXX ADULT MINUTES PER DEVICE")
    logger.info("-" * 70)
    minutes_stats = compute_xxx_minutes_per_device(df)
    minutes_stats.to_csv(OUTPUT_DIR / f'mobile_xxx_minutes_per_device_{MONTH_ID}.csv', index=False)

    # 3. Top sites
    logger.info("\n" + "-" * 70)
    logger.info("3. TOP XXX ADULT WEBSITES")
    logger.info("-" * 70)
    by_sessions, by_minutes = compute_top_xxx_sites(df)
    by_sessions.to_csv(OUTPUT_DIR / f'mobile_xxx_top_sites_by_sessions_{MONTH_ID}.csv', index=False)
    by_minutes.to_csv(OUTPUT_DIR / f'mobile_xxx_top_sites_by_minutes_{MONTH_ID}.csv', index=False)

    # Done
    logger.info("\n" + "=" * 70)
    logger.info("COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Output saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
