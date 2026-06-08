"""
Session Summary Statistics

This script produces diagnostic summary statistics on the merged sessions file,
focusing on XXX Adult subcategory visit patterns.

Usage:
    python code/descriptives/session_summary_statistics.py
    python code/descriptives/session_summary_statistics.py --sample 100000  # Use 100k row sample

Outputs:
    - output/descriptives/session_summary_202201.csv
    - output/descriptives/top_websites_202201.csv
    - output/descriptives/top_xxx_adult_websites_202201.csv
    - output/descriptives/top_xxx_adult_websites_202201.png
    - output/descriptives/category_frequency_202201.png
    - output/descriptives/websites_and_categories_202201.png
    - output/descriptives/cumulative_xxx_visits_202201.png
    - output/descriptives/minutes_per_visit_202201.png
    - output/descriptives/gender_visit_frequency_202201.png
    - output/descriptives/male_demographics_202201.png
    - output/descriptives/daily_time_online_202201.csv
    - output/descriptives/machine_person_sharing_202201.csv
    - output/descriptives/session_length_by_website_202201.csv
    - output/descriptives/session_length_by_category_202201.csv
    - output/descriptives/website_overlap_matrix_202201.csv
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import logging
import sys

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'code'))

import matplotlib.pyplot as plt
from plot_style import apply_plot_style, UCHICAGO_MAROON, COLOR_PALETTE

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Base directory (current working directory)
BASE_DIR = Path.cwd()

# Paths
DATA_DIR = BASE_DIR / 'data' / 'ProcessComscore' / 'merged_session_files'
OUTPUT_DIR = BASE_DIR / 'output' / 'descriptives'

# Time conversion: time_id is days since Jan 1, 2000
TIME_ID_EPOCH = datetime(2000, 1, 1)


def time_id_to_date(time_id):
    """Convert time_id to datetime."""
    return TIME_ID_EPOCH + timedelta(days=int(time_id))


def load_merged_sessions(month_id):
    """
    Load merged sessions parquet file.

    Args:
        month_id: Month ID string (e.g., '202201')

    Returns:
        DataFrame with merged session data
    """
    logger.info(f"Loading merged sessions for {month_id}...")

    file_path = DATA_DIR / f'merged_sessions_{month_id}.parquet'

    if not file_path.exists():
        raise FileNotFoundError(f"Merged sessions file not found: {file_path}")

    df = pd.read_parquet(
        file_path,
        dtype_backend='numpy_nullable'
    )

    # Ensure IDs are strings
    for col in ['machine_id', 'person_id', 'pattern_id']:
        if col in df.columns:
            df[col] = df[col].astype(str)

    logger.info(f"  Loaded {len(df):,} sessions")

    return df


def compute_overall_summary(df):
    """
    Compute overall dataset summary statistics.

    Args:
        df: Merged sessions DataFrame

    Returns:
        Dictionary of summary statistics
    """
    logger.info("Computing overall summary statistics...")

    summary = {
        'total_sessions': len(df),
        'unique_machines': df['machine_id'].nunique(),
        'unique_persons': df['person_id'].nunique(),
        'unique_top_web_ids': df['top_web_id'].nunique() if 'top_web_id' in df.columns else np.nan,
        'unique_pattern_ids': df['pattern_id'].nunique(),
        'unique_categories': df['category'].nunique() if 'category' in df.columns else np.nan,
        'unique_subcategories': df['subcategory'].nunique() if 'subcategory' in df.columns else np.nan,
    }

    logger.info(f"  Total sessions: {summary['total_sessions']:,}")
    logger.info(f"  Unique machines: {summary['unique_machines']:,}")
    logger.info(f"  Unique persons: {summary['unique_persons']:,}")
    logger.info(f"  Unique top_web_ids: {summary['unique_top_web_ids']:,}")
    logger.info(f"  Unique categories: {summary['unique_categories']:,}")
    logger.info(f"  Unique subcategories: {summary['unique_subcategories']:,}")

    return summary


def compute_xxx_adult_summary(df):
    """
    Compute XXX Adult subcategory summary statistics.

    Args:
        df: Merged sessions DataFrame

    Returns:
        Dictionary of XXX Adult summary statistics
    """
    logger.info("Computing XXX Adult category statistics...")

    # Filter to XXX Adult subcategory
    xxx_adult_df = df[df['subcategory'] == 'XXX Adult']

    total_sessions = len(df)
    xxx_sessions = len(xxx_adult_df)

    total_machines = df['machine_id'].nunique()
    total_persons = df['person_id'].nunique()
    total_pattern_ids = df['pattern_id'].nunique()
    total_top_web_ids = df['top_web_id'].nunique() if 'top_web_id' in df.columns else 0

    xxx_machines = xxx_adult_df['machine_id'].nunique()
    xxx_persons = xxx_adult_df['person_id'].nunique()
    xxx_pattern_ids = xxx_adult_df['pattern_id'].nunique()
    xxx_top_web_ids = xxx_adult_df['top_web_id'].nunique() if 'top_web_id' in xxx_adult_df.columns else 0

    summary = {
        'xxx_adult_sessions': xxx_sessions,
        'xxx_adult_sessions_pct': (xxx_sessions / total_sessions * 100) if total_sessions > 0 else 0,
        'xxx_adult_machines': xxx_machines,
        'xxx_adult_machines_pct': (xxx_machines / total_machines * 100) if total_machines > 0 else 0,
        'xxx_adult_persons': xxx_persons,
        'xxx_adult_persons_pct': (xxx_persons / total_persons * 100) if total_persons > 0 else 0,
        'xxx_adult_pattern_ids': xxx_pattern_ids,
        'xxx_adult_pattern_ids_pct': (xxx_pattern_ids / total_pattern_ids * 100) if total_pattern_ids > 0 else 0,
        'xxx_adult_top_web_ids': xxx_top_web_ids,
        'xxx_adult_top_web_ids_pct': (xxx_top_web_ids / total_top_web_ids * 100) if total_top_web_ids > 0 else 0,
    }

    logger.info(f"  XXX Adult sessions: {xxx_sessions:,} ({summary['xxx_adult_sessions_pct']:.2f}%)")
    logger.info(f"  XXX Adult machines: {xxx_machines:,} ({summary['xxx_adult_machines_pct']:.2f}%)")
    logger.info(f"  XXX Adult persons: {xxx_persons:,} ({summary['xxx_adult_persons_pct']:.2f}%)")
    logger.info(f"  XXX Adult pattern_ids: {xxx_pattern_ids:,} ({summary['xxx_adult_pattern_ids_pct']:.2f}%)")
    logger.info(f"  XXX Adult top_web_ids: {xxx_top_web_ids:,} ({summary['xxx_adult_top_web_ids_pct']:.2f}%)")

    return summary


def compute_top_websites(df, top_n=50):
    """
    Compute ranked list of top websites overall with their categories.
    If category is NA but subcategory exists, uses subcategory as the category.

    Args:
        df: Merged sessions DataFrame
        top_n: Number of top websites to return

    Returns:
        DataFrame with ranked website list including category info
    """
    logger.info(f"Computing top {top_n} websites overall...")

    total_sessions = len(df)
    total_duration = df['duration'].sum()

    # Group by website only (not category) to properly aggregate
    website_counts = df.groupby(['top_web_id', 'top_web_name']).agg(
        session_count=('session_id', 'size'),
        total_duration=('duration', 'sum')
    ).reset_index()

    # Get category info separately (take first non-null if available)
    category_info = df.groupby(['top_web_id', 'top_web_name']).agg({
        'category': 'first',
        'subcategory': 'first'
    }).reset_index()

    # Merge
    website_counts = website_counts.merge(category_info, on=['top_web_id', 'top_web_name'], how='left')

    # Sort by session count descending
    website_counts = website_counts.sort_values('session_count', ascending=False)

    # Add rank and percentages
    website_counts['rank'] = range(1, len(website_counts) + 1)
    website_counts['session_pct'] = website_counts['session_count'] / total_sessions * 100
    website_counts['duration_pct'] = website_counts['total_duration'] / total_duration * 100

    # If category is NA but subcategory exists, use subcategory as category
    website_counts['category'] = website_counts['category'].fillna(website_counts['subcategory'])

    # Mark remaining uncategorized
    website_counts['category'] = website_counts['category'].fillna('Uncategorized')

    # Reorder columns
    website_counts = website_counts[['rank', 'top_web_id', 'top_web_name', 'category', 'subcategory',
                                      'session_count', 'session_pct', 'total_duration', 'duration_pct']]

    logger.info(f"  Found {len(website_counts):,} unique websites")

    return website_counts.head(top_n)


def compute_top_xxx_adult_websites(df, top_n=50):
    """
    Compute ranked list of top websites in XXX Adult subcategory.
    Also computes "all other sites" aggregate.

    Args:
        df: Merged sessions DataFrame
        top_n: Number of top websites to return

    Returns:
        Tuple of (top_websites DataFrame, total_xxx_sessions, total_xxx_duration)
    """
    logger.info(f"Computing top {top_n} XXX Adult websites...")

    # Filter to XXX Adult subcategory
    xxx_adult_df = df[df['subcategory'] == 'XXX Adult']
    total_xxx_sessions = len(xxx_adult_df)
    total_xxx_duration = xxx_adult_df['duration'].sum()

    # Group by website and count sessions and duration
    website_counts = xxx_adult_df.groupby(
        ['top_web_id', 'top_web_name']
    ).agg(
        session_count=('session_id', 'size'),
        total_duration=('duration', 'sum')
    ).reset_index()

    # Sort by session count descending
    website_counts = website_counts.sort_values('session_count', ascending=False)

    # Add rank and percentages
    website_counts['rank'] = range(1, len(website_counts) + 1)
    website_counts['session_pct'] = website_counts['session_count'] / total_xxx_sessions * 100
    website_counts['duration_pct'] = website_counts['total_duration'] / total_xxx_duration * 100

    # Reorder columns
    website_counts = website_counts[['rank', 'top_web_id', 'top_web_name', 'session_count',
                                      'session_pct', 'total_duration', 'duration_pct']]

    logger.info(f"  Found {len(website_counts):,} unique XXX Adult websites")

    return website_counts.head(top_n), total_xxx_sessions, total_xxx_duration


def compute_category_frequency(df):
    """
    Compute category frequency by sessions and total duration.
    If category is NA but subcategory exists, uses subcategory as the category.

    Args:
        df: Merged sessions DataFrame

    Returns:
        DataFrame with category frequencies
    """
    logger.info("Computing category frequency statistics...")

    total_sessions = len(df)
    total_duration = df['duration'].sum()

    # Create effective category: use subcategory if category is NA
    df = df.copy()
    df['effective_category'] = df['category'].fillna(df['subcategory'])

    # Group by effective category
    category_stats = df.groupby('effective_category').agg(
        session_count=('session_id', 'size'),
        total_duration=('duration', 'sum')
    ).reset_index()
    category_stats = category_stats.rename(columns={'effective_category': 'category'})

    # Add percentages (relative to total dataset)
    category_stats['session_pct'] = category_stats['session_count'] / total_sessions * 100
    category_stats['duration_pct'] = category_stats['total_duration'] / total_duration * 100

    # Sort by session count
    category_stats = category_stats.sort_values('session_count', ascending=False)

    # Add rank
    category_stats['rank'] = range(1, len(category_stats) + 1)

    logger.info(f"  Found {len(category_stats):,} categories")

    return category_stats


def compute_cumulative_xxx_visits(df):
    """
    Compute cumulative XXX Adult visit statistics over time.
    For each date, compute share of all people who have visited at least N days.

    Args:
        df: Merged sessions DataFrame

    Returns:
        Tuple of (cumulative_days_df, cumulative_minutes_df)
    """
    logger.info("Computing cumulative XXX Adult visit statistics...")

    total_persons = df['person_id'].nunique()

    # Filter to XXX Adult
    xxx_df = df[df['subcategory'] == 'XXX Adult'].copy()

    # Get sorted list of unique time_ids (dates)
    time_ids = sorted(xxx_df['time_id'].unique())

    # For each person, track cumulative days and minutes
    person_daily = xxx_df.groupby(['person_id', 'time_id']).agg(
        daily_duration=('duration', 'sum')
    ).reset_index()

    # Build cumulative stats by date
    cumulative_days_data = []
    cumulative_minutes_data = []

    for current_time_id in time_ids:
        current_date = time_id_to_date(current_time_id)

        # Get all visits up to and including this date
        visits_so_far = person_daily[person_daily['time_id'] <= current_time_id]

        # Count days per person up to this date
        days_per_person = visits_so_far.groupby('person_id').size()

        # Count total minutes per person up to this date
        minutes_per_person = visits_so_far.groupby('person_id')['daily_duration'].sum() / 60

        # Compute share with at least N days
        for n in [1, 2, 3, 4, 5]:
            count = (days_per_person >= n).sum()
            cumulative_days_data.append({
                'time_id': current_time_id,
                'date': current_date,
                'threshold': n,
                'num_persons': count,
                'share_of_all': count / total_persons * 100
            })

        # Compute share with at least N minutes (10, 30, 60, 120, 300)
        for n in [10, 30, 60, 120, 300]:
            count = (minutes_per_person >= n).sum()
            cumulative_minutes_data.append({
                'time_id': current_time_id,
                'date': current_date,
                'threshold_minutes': n,
                'num_persons': count,
                'share_of_all': count / total_persons * 100
            })

    cumulative_days_df = pd.DataFrame(cumulative_days_data)
    cumulative_minutes_df = pd.DataFrame(cumulative_minutes_data)

    logger.info(f"  Computed cumulative stats for {len(time_ids)} days")

    return cumulative_days_df, cumulative_minutes_df


def compute_minutes_per_visit(df):
    """
    Compute distribution of minutes per visit for XXX Adult sessions.

    Args:
        df: Merged sessions DataFrame

    Returns:
        DataFrame with minutes per visit distribution
    """
    logger.info("Computing minutes per visit distribution...")

    # Filter to XXX Adult
    xxx_df = df[df['subcategory'] == 'XXX Adult'].copy()

    # Convert duration to minutes
    xxx_df['minutes'] = xxx_df['duration'] / 60

    # Compute statistics
    stats = {
        'mean': xxx_df['minutes'].mean(),
        'median': xxx_df['minutes'].median(),
        'std': xxx_df['minutes'].std(),
        'min': xxx_df['minutes'].min(),
        'max': xxx_df['minutes'].max(),
        'p25': xxx_df['minutes'].quantile(0.25),
        'p75': xxx_df['minutes'].quantile(0.75),
        'p90': xxx_df['minutes'].quantile(0.90),
        'p95': xxx_df['minutes'].quantile(0.95),
        'p99': xxx_df['minutes'].quantile(0.99),
    }

    logger.info(f"  Mean minutes per visit: {stats['mean']:.2f}")
    logger.info(f"  Median minutes per visit: {stats['median']:.2f}")

    return xxx_df['minutes'], stats


def compute_gender_visit_frequency(df):
    """
    Compute XXX Adult visit frequency by gender.
    Buckets: 1 day, 2-3 days, 4-10 days, 10+ days (excluding 0 days)

    Args:
        df: Merged sessions DataFrame

    Returns:
        DataFrame with gender visit frequency
    """
    logger.info("Computing gender-based visit frequency...")

    # Get all persons with their gender
    person_gender = df.groupby('person_id')['person_gender'].first().reset_index()

    # Filter to Male/Female only
    person_gender = person_gender[person_gender['person_gender'].isin(['Male', 'Female'])]

    # Get XXX Adult visits per person
    xxx_df = df[df['subcategory'] == 'XXX Adult']
    xxx_days = xxx_df.groupby('person_id')['time_id'].nunique().reset_index()
    xxx_days.columns = ['person_id', 'num_days']

    # Merge: persons without XXX visits get 0 days
    person_visits = person_gender.merge(xxx_days, on='person_id', how='left')
    person_visits['num_days'] = person_visits['num_days'].fillna(0).astype(int)

    # Create buckets
    def bucket_days(n):
        if n == 0:
            return '0 days'
        elif n == 1:
            return '1 day'
        elif n <= 3:
            return '2-3 days'
        elif n <= 10:
            return '4-10 days'
        else:
            return '10+ days'

    person_visits['bucket'] = person_visits['num_days'].apply(bucket_days)

    # Count by gender and bucket
    gender_counts = person_visits.groupby(['person_gender', 'bucket']).size().reset_index(name='count')

    # Compute shares within each gender
    gender_totals = person_visits.groupby('person_gender').size().reset_index(name='total')
    gender_counts = gender_counts.merge(gender_totals, on='person_gender')
    gender_counts['share'] = gender_counts['count'] / gender_counts['total'] * 100

    logger.info(f"  Males: {gender_totals[gender_totals['person_gender']=='Male']['total'].iloc[0]:,}")
    logger.info(f"  Females: {gender_totals[gender_totals['person_gender']=='Female']['total'].iloc[0]:,}")

    return gender_counts, person_visits


def compute_daily_time_online(df):
    """
    Compute distribution of total time online at the day-machine level.
    Flags any rows where total minutes > 1440 (24 hours).

    Args:
        df: Merged sessions DataFrame

    Returns:
        DataFrame with summary statistics (p25, median, p75, p90, p99, max, count_over_24h)
    """
    logger.info("Computing daily time online distribution...")

    # Group by machine_id and time_id, sum duration (in seconds)
    daily_time = df.groupby(['machine_id', 'time_id']).agg(
        total_duration_seconds=('duration', 'sum'),
        session_count=('session_id', 'size')
    ).reset_index()

    # Convert to minutes
    daily_time['total_minutes'] = daily_time['total_duration_seconds'] / 60

    # Flag rows where total minutes > 1440 (24 hours)
    count_over_24h = (daily_time['total_minutes'] > 1440).sum()

    # Create summary stats DataFrame
    stats_df = pd.DataFrame([{
        'total_day_machine_obs': len(daily_time),
        'p25': daily_time['total_minutes'].quantile(0.25),
        'median': daily_time['total_minutes'].median(),
        'p75': daily_time['total_minutes'].quantile(0.75),
        'p90': daily_time['total_minutes'].quantile(0.90),
        'p99': daily_time['total_minutes'].quantile(0.99),
        'max': daily_time['total_minutes'].max(),
        'count_over_24h': count_over_24h,
        'pct_over_24h': count_over_24h / len(daily_time) * 100 if len(daily_time) > 0 else 0,
    }])

    logger.info(f"  Total day-machine observations: {len(daily_time):,}")
    logger.info(f"  Median daily minutes: {stats_df['median'].iloc[0]:.2f}")
    logger.info(f"  Max daily minutes: {stats_df['max'].iloc[0]:.2f}")
    logger.info(f"  Observations > 24 hours: {count_over_24h:,} ({stats_df['pct_over_24h'].iloc[0]:.4f}%)")

    return stats_df


def compute_machine_person_sharing(df):
    """
    Compute how common it is for the same machine to have different people in the same month.

    Args:
        df: Merged sessions DataFrame

    Returns:
        Tuple of (sharing_df, distribution_df)
    """
    logger.info("Computing machine-person sharing statistics...")

    # Group by machine_id and count unique person_ids
    machine_persons = df.groupby('machine_id')['person_id'].nunique().reset_index()
    machine_persons.columns = ['machine_id', 'unique_persons']

    # Create distribution: how many machines have 1, 2, 3+ persons
    def bucket_persons(n):
        if n == 1:
            return '1 person'
        elif n == 2:
            return '2 persons'
        else:
            return '3+ persons'

    machine_persons['bucket'] = machine_persons['unique_persons'].apply(bucket_persons)

    # Count machines in each bucket
    distribution = machine_persons.groupby('bucket').size().reset_index(name='machine_count')
    distribution['pct_of_machines'] = distribution['machine_count'] / len(machine_persons) * 100

    # Ensure proper ordering
    bucket_order = ['1 person', '2 persons', '3+ persons']
    distribution['bucket'] = pd.Categorical(distribution['bucket'], categories=bucket_order, ordered=True)
    distribution = distribution.sort_values('bucket').reset_index(drop=True)

    # Also compute summary stats
    total_machines = len(machine_persons)
    machines_with_sharing = (machine_persons['unique_persons'] > 1).sum()

    logger.info(f"  Total machines: {total_machines:,}")
    logger.info(f"  Machines with >1 person: {machines_with_sharing:,} ({machines_with_sharing/total_machines*100:.2f}%)")
    for _, row in distribution.iterrows():
        logger.info(f"    {row['bucket']}: {row['machine_count']:,} ({row['pct_of_machines']:.2f}%)")

    return machine_persons, distribution


def compute_session_length_stats(df, top_n=30):
    """
    Compute session length stats for top N websites and categories.
    For each item: mean, median, p90, p99, max duration; share of machines, total sessions, total hours.

    Args:
        df: Merged sessions DataFrame
        top_n: Number of top websites/categories to include

    Returns:
        Tuple of (website_stats_df, category_stats_df)
    """
    logger.info(f"Computing session length stats for top {top_n} websites and categories...")

    total_machines = df['machine_id'].nunique()

    # Convert duration to minutes for stats
    df = df.copy()
    df['duration_minutes'] = df['duration'] / 60

    # --- Top 30 websites by session count ---
    website_sessions = df.groupby(['top_web_id', 'top_web_name']).size().reset_index(name='session_count')
    top_websites = website_sessions.nlargest(top_n, 'session_count')

    website_stats_list = []
    for _, row in top_websites.iterrows():
        web_id, web_name = row['top_web_id'], row['top_web_name']
        subset = df[(df['top_web_id'] == web_id) & (df['top_web_name'] == web_name)]

        stats = {
            'top_web_id': web_id,
            'top_web_name': web_name,
            'session_count': len(subset),
            'total_hours': subset['duration'].sum() / 3600,
            'machines_visiting': subset['machine_id'].nunique(),
            'share_of_machines': subset['machine_id'].nunique() / total_machines * 100,
            'mean_minutes': subset['duration_minutes'].mean(),
            'median_minutes': subset['duration_minutes'].median(),
            'p90_minutes': subset['duration_minutes'].quantile(0.90),
            'p99_minutes': subset['duration_minutes'].quantile(0.99),
            'max_minutes': subset['duration_minutes'].max(),
        }
        website_stats_list.append(stats)

    website_stats_df = pd.DataFrame(website_stats_list)
    website_stats_df['rank'] = range(1, len(website_stats_df) + 1)
    # Reorder columns
    website_stats_df = website_stats_df[['rank', 'top_web_id', 'top_web_name', 'session_count', 'total_hours',
                                          'machines_visiting', 'share_of_machines', 'mean_minutes',
                                          'median_minutes', 'p90_minutes', 'p99_minutes', 'max_minutes']]

    # --- Top 30 categories by session count ---
    # Use subcategory if category is NA
    df['effective_category'] = df['category'].fillna(df['subcategory'])
    category_sessions = df.groupby('effective_category').size().reset_index(name='session_count')
    top_categories = category_sessions.nlargest(top_n, 'session_count')

    category_stats_list = []
    for _, row in top_categories.iterrows():
        category = row['effective_category']
        subset = df[df['effective_category'] == category]

        stats = {
            'category': category,
            'session_count': len(subset),
            'total_hours': subset['duration'].sum() / 3600,
            'machines_visiting': subset['machine_id'].nunique(),
            'share_of_machines': subset['machine_id'].nunique() / total_machines * 100,
            'mean_minutes': subset['duration_minutes'].mean(),
            'median_minutes': subset['duration_minutes'].median(),
            'p90_minutes': subset['duration_minutes'].quantile(0.90),
            'p99_minutes': subset['duration_minutes'].quantile(0.99),
            'max_minutes': subset['duration_minutes'].max(),
        }
        category_stats_list.append(stats)

    category_stats_df = pd.DataFrame(category_stats_list)
    category_stats_df['rank'] = range(1, len(category_stats_df) + 1)
    # Reorder columns
    category_stats_df = category_stats_df[['rank', 'category', 'session_count', 'total_hours',
                                            'machines_visiting', 'share_of_machines', 'mean_minutes',
                                            'median_minutes', 'p90_minutes', 'p99_minutes', 'max_minutes']]

    logger.info(f"  Computed stats for {len(website_stats_df)} websites and {len(category_stats_df)} categories")

    return website_stats_df, category_stats_df


def compute_website_overlap_matrix(df, top_n=5):
    """
    Compute overlap matrix for top N XXX Adult websites.
    For each pair (row, col): fraction of machines visiting row website that also visit column website.
    Last column shows raw share of all machines visiting the row website.

    Args:
        df: Merged sessions DataFrame
        top_n: Number of top XXX Adult websites to include

    Returns:
        DataFrame with overlap matrix
    """
    logger.info(f"Computing website overlap matrix for top {top_n} XXX Adult websites...")

    total_machines = df['machine_id'].nunique()

    # Filter to XXX Adult subcategory and identify top N websites by session count
    xxx_df = df[df['subcategory'] == 'XXX Adult']
    website_sessions = xxx_df.groupby(['top_web_id', 'top_web_name']).size().reset_index(name='session_count')
    top_websites = website_sessions.nlargest(top_n, 'session_count')
    top_web_ids = top_websites['top_web_id'].tolist()
    top_web_names = top_websites['top_web_name'].tolist()

    # Get set of machines visiting each top XXX Adult website
    machines_by_site = {}
    for web_id, web_name in zip(top_web_ids, top_web_names):
        machines_by_site[web_name] = set(
            xxx_df[(xxx_df['top_web_id'] == web_id) & (xxx_df['top_web_name'] == web_name)]['machine_id'].unique()
        )

    # Build overlap matrix
    matrix_data = []
    for row_name in top_web_names:
        row_machines = machines_by_site[row_name]
        row_data = {'website': row_name}

        # Overlap with each column website
        for col_name in top_web_names:
            col_machines = machines_by_site[col_name]
            overlap = len(row_machines & col_machines)
            row_data[col_name] = overlap / len(row_machines) * 100 if len(row_machines) > 0 else 0

        # Add raw share of all machines visiting this row website
        row_data['share_of_all_machines'] = len(row_machines) / total_machines * 100

        matrix_data.append(row_data)

    matrix_df = pd.DataFrame(matrix_data)

    logger.info(f"  Created {top_n}x{top_n} overlap matrix")
    logger.info(f"  Total machines: {total_machines:,}")

    return matrix_df


def compute_male_demographics(df):
    """
    Compute XXX Adult visit frequency for males by demographic splits.

    Args:
        df: Merged sessions DataFrame

    Returns:
        Dictionary of DataFrames with demographic splits
    """
    logger.info("Computing male demographic splits for XXX Adult visits...")

    # Get all male persons with their demographics
    males = df[df['person_gender'] == 'Male'].groupby('person_id').agg({
        'age_range': 'first',
        'HHI': 'first',
        'person_race': 'first',
        'person_ethnicity': 'first'
    }).reset_index()

    # Get XXX Adult visits per person
    xxx_df = df[df['subcategory'] == 'XXX Adult']
    xxx_days = xxx_df.groupby('person_id')['time_id'].nunique().reset_index()
    xxx_days.columns = ['person_id', 'num_days']

    # Merge
    male_visits = males.merge(xxx_days, on='person_id', how='left')
    male_visits['num_days'] = male_visits['num_days'].fillna(0).astype(int)

    # Create buckets (excluding 0 days for the plot)
    def bucket_days(n):
        if n == 0:
            return '0 days'
        elif n == 1:
            return '1 day'
        elif n <= 3:
            return '2-3 days'
        elif n <= 10:
            return '4-10 days'
        else:
            return '10+ days'

    male_visits['bucket'] = male_visits['num_days'].apply(bucket_days)

    results = {}

    # Age range analysis
    age_counts = male_visits.groupby(['age_range', 'bucket']).size().reset_index(name='count')
    age_totals = male_visits.groupby('age_range').size().reset_index(name='total')
    age_counts = age_counts.merge(age_totals, on='age_range')
    age_counts['share'] = age_counts['count'] / age_counts['total'] * 100
    results['age_range'] = age_counts

    # HHI analysis
    hhi_counts = male_visits.groupby(['HHI', 'bucket']).size().reset_index(name='count')
    hhi_totals = male_visits.groupby('HHI').size().reset_index(name='total')
    hhi_counts = hhi_counts.merge(hhi_totals, on='HHI')
    hhi_counts['share'] = hhi_counts['count'] / hhi_counts['total'] * 100
    results['HHI'] = hhi_counts

    # Race analysis
    race_counts = male_visits.groupby(['person_race', 'bucket']).size().reset_index(name='count')
    race_totals = male_visits.groupby('person_race').size().reset_index(name='total')
    race_counts = race_counts.merge(race_totals, on='person_race')
    race_counts['share'] = race_counts['count'] / race_counts['total'] * 100
    results['race'] = race_counts

    logger.info(f"  Total males: {len(males):,}")

    return results, male_visits


def create_summary_table(overall_summary, xxx_summary):
    """
    Create summary statistics table for export.

    Args:
        overall_summary: Dictionary of overall statistics
        xxx_summary: Dictionary of XXX Adult statistics

    Returns:
        DataFrame with summary statistics
    """
    rows = [
        # Overall statistics
        {'metric': 'Total Sessions', 'value': overall_summary['total_sessions'], 'pct_of_total': 100.0},
        {'metric': 'Unique Machines', 'value': overall_summary['unique_machines'], 'pct_of_total': 100.0},
        {'metric': 'Unique Persons', 'value': overall_summary['unique_persons'], 'pct_of_total': 100.0},
        {'metric': 'Unique Websites (top_web_id)', 'value': overall_summary['unique_top_web_ids'], 'pct_of_total': 100.0},
        {'metric': 'Unique Pattern IDs', 'value': overall_summary['unique_pattern_ids'], 'pct_of_total': 100.0},
        {'metric': 'Unique Categories', 'value': overall_summary['unique_categories'], 'pct_of_total': 100.0},
        {'metric': 'Unique Subcategories', 'value': overall_summary['unique_subcategories'], 'pct_of_total': 100.0},
        # XXX Adult statistics
        {'metric': 'XXX Adult Sessions', 'value': xxx_summary['xxx_adult_sessions'], 'pct_of_total': xxx_summary['xxx_adult_sessions_pct']},
        {'metric': 'XXX Adult Machines', 'value': xxx_summary['xxx_adult_machines'], 'pct_of_total': xxx_summary['xxx_adult_machines_pct']},
        {'metric': 'XXX Adult Persons', 'value': xxx_summary['xxx_adult_persons'], 'pct_of_total': xxx_summary['xxx_adult_persons_pct']},
        {'metric': 'XXX Adult Websites', 'value': xxx_summary['xxx_adult_top_web_ids'], 'pct_of_total': xxx_summary['xxx_adult_top_web_ids_pct']},
        {'metric': 'XXX Adult Pattern IDs', 'value': xxx_summary['xxx_adult_pattern_ids'], 'pct_of_total': xxx_summary['xxx_adult_pattern_ids_pct']},
    ]

    return pd.DataFrame(rows)


def plot_top_xxx_adult_websites(website_df, total_xxx_sessions, total_xxx_duration, output_path, top_n=20):
    """
    Create dual-panel horizontal bar chart of top XXX Adult websites with "all other" line.
    Shows share of sessions and share of time spent.

    Args:
        website_df: DataFrame with ranked website data
        total_xxx_sessions: Total XXX Adult sessions for computing "all other"
        total_xxx_duration: Total XXX Adult duration for computing "all other"
        output_path: Path to save the plot
        top_n: Number of websites to include in chart
    """
    logger.info(f"Creating top {top_n} XXX Adult websites chart...")

    # Apply house style
    apply_plot_style()

    # Get top N websites
    top_websites = website_df.head(top_n).copy()

    # Calculate "all other" sessions and duration
    top_sessions = top_websites['session_count'].sum()
    other_sessions = total_xxx_sessions - top_sessions
    other_session_pct = other_sessions / total_xxx_sessions * 100

    top_duration = top_websites['total_duration'].sum()
    other_duration = total_xxx_duration - top_duration
    other_duration_pct = other_duration / total_xxx_duration * 100

    # Add "all other" row
    other_row = pd.DataFrame([{
        'rank': top_n + 1,
        'top_web_id': 'other',
        'top_web_name': 'All Other Sites',
        'session_count': other_sessions,
        'session_pct': other_session_pct,
        'total_duration': other_duration,
        'duration_pct': other_duration_pct
    }])
    plot_data = pd.concat([top_websites, other_row], ignore_index=True)

    # Create dual-panel figure
    fig, axes = plt.subplots(1, 2, figsize=(14, 9))

    y_pos = range(len(plot_data))
    colors = [UCHICAGO_MAROON] * top_n + ['#767676']  # Gray for "all other"

    # Create labels with ranking numbers
    labels = []
    for _, row in plot_data.iterrows():
        if row['top_web_name'] == 'All Other Sites':
            labels.append(row['top_web_name'])
        else:
            labels.append(f"{int(row['rank'])}. {row['top_web_name']}")

    # Left panel: By share of sessions
    ax1 = axes[0]
    ax1.barh(y_pos, plot_data['session_pct'], color=colors)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(labels)
    ax1.invert_yaxis()
    ax1.set_xlabel('Share of XXX Adult Sessions (%)')
    ax1.set_title('By Session Count')

    # Right panel: By share of duration
    ax2 = axes[1]
    ax2.barh(y_pos, plot_data['duration_pct'], color=colors)
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(labels)
    ax2.invert_yaxis()
    ax2.set_xlabel('Share of XXX Adult Hours (%)')
    ax2.set_title('By Time Spent')

    fig.suptitle(f'Top {top_n} Websites in XXX Adult Subcategory', fontsize=14, y=1.02)
    plt.tight_layout()

    # Save
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    logger.info(f"  Chart saved to: {output_path}")


def plot_category_frequency(category_df, output_path, top_n=20):
    """
    Create dual bar chart of category frequency by share of sessions and hours.

    Args:
        category_df: DataFrame with category frequency data
        output_path: Path to save the plot
        top_n: Number of categories to include
    """
    logger.info(f"Creating category frequency chart (top {top_n})...")

    apply_plot_style()

    top_categories = category_df.head(top_n)

    fig, axes = plt.subplots(1, 2, figsize=(14, 8))

    # Left: By share of sessions
    ax1 = axes[0]
    y_pos = range(len(top_categories))

    # Highlight XXX Adult row
    colors = [UCHICAGO_MAROON if 'XXX Adult' not in cat else '#C16622'
              for cat in top_categories['category']]

    ax1.barh(y_pos, top_categories['session_pct'], color=colors)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels([f"{r}. {c}" for r, c in zip(top_categories['rank'], top_categories['category'])])
    ax1.invert_yaxis()
    ax1.set_xlabel('Share of All Sessions (%)')
    ax1.set_title('By Session Count')

    # Right: By share of duration
    ax2 = axes[1]
    ax2.barh(y_pos, top_categories['duration_pct'], color=colors)
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels([f"{r}. {c}" for r, c in zip(top_categories['rank'], top_categories['category'])])
    ax2.invert_yaxis()
    ax2.set_xlabel('Share of All Hours (%)')
    ax2.set_title('By Time Spent')

    fig.suptitle(f'Top {top_n} Categories (XXX Adult highlighted in orange)', fontsize=14, y=1.02)
    plt.tight_layout()

    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    logger.info(f"  Chart saved to: {output_path}")


def plot_websites_and_categories(top_websites_df, category_df, output_path, n_websites=10, n_categories=20):
    """
    Create dual-panel combined plot showing top websites intermingled with categories.
    Mirrors the category frequency plot with both sessions and duration panels.
    Includes uncategorized websites and highlights XXX Adult.

    Args:
        top_websites_df: DataFrame with top websites
        category_df: DataFrame with category frequencies
        output_path: Path to save the plot
        n_websites: Number of top websites to include
        n_categories: Number of categories to include
    """
    logger.info(f"Creating combined websites and categories chart...")

    apply_plot_style()

    # Get top websites (including uncategorized)
    top_websites = top_websites_df.head(n_websites).copy()
    top_websites['type'] = 'website'
    top_websites['name'] = top_websites['top_web_name']

    # Get top categories (XXX Adult will appear as a category since subcategory fills NA)
    top_cats = category_df.head(n_categories).copy()
    top_cats['type'] = 'category'
    top_cats['name'] = top_cats['category']

    # Combine and sort by session_pct
    combined = pd.concat([
        top_websites[['name', 'session_pct', 'duration_pct', 'type', 'category']],
        top_cats[['name', 'session_pct', 'duration_pct', 'type']]
    ], ignore_index=True)

    # Add category info for categories
    combined.loc[combined['type'] == 'category', 'category'] = combined.loc[combined['type'] == 'category', 'name']

    combined = combined.sort_values('session_pct', ascending=False).head(n_websites + n_categories)
    combined['rank'] = range(1, len(combined) + 1)

    # Create dual-panel figure
    fig, axes = plt.subplots(1, 2, figsize=(16, 10))

    y_pos = range(len(combined))

    # Determine colors: orange for websites, maroon for categories, gold for XXX Adult
    def get_color(row):
        # XXX Adult (subcategory) highlighted in gold
        if 'XXX Adult' in str(row['name']):
            return '#E69F00'  # Gold/orange for XXX Adult
        elif row['type'] == 'website':
            return '#0072B2'  # Blue for websites
        else:
            return UCHICAGO_MAROON  # Maroon for categories

    colors = [get_color(row) for _, row in combined.iterrows()]

    # Create labels
    labels = []
    for _, row in combined.iterrows():
        if row['type'] == 'website':
            cat_label = f" [{row['category']}]" if pd.notna(row['category']) and row['category'] != 'Uncategorized' else " [Uncategorized]"
            labels.append(f"{row['rank']}. {row['name']}{cat_label}")
        else:
            labels.append(f"{row['rank']}. {row['name']} (category)")

    # Left panel: By share of sessions
    ax1 = axes[0]
    ax1.barh(y_pos, combined['session_pct'], color=colors)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(labels, fontsize=9)
    ax1.invert_yaxis()
    ax1.set_xlabel('Share of All Sessions (%)')
    ax1.set_title('By Session Count')

    # Right panel: By share of duration
    ax2 = axes[1]
    ax2.barh(y_pos, combined['duration_pct'], color=colors)
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(labels, fontsize=9)
    ax2.invert_yaxis()
    ax2.set_xlabel('Share of All Hours (%)')
    ax2.set_title('By Time Spent')

    fig.suptitle('Top Websites and Categories Combined\n(Blue = Website, Maroon = Category, Gold = XXX Adult)',
                 fontsize=14, y=1.02)
    plt.tight_layout()

    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    logger.info(f"  Chart saved to: {output_path}")


def plot_cumulative_xxx_visits(cumulative_days_df, cumulative_minutes_df, output_path):
    """
    Create plots showing cumulative XXX Adult visit patterns over time.

    Args:
        cumulative_days_df: DataFrame with cumulative days thresholds
        cumulative_minutes_df: DataFrame with cumulative minutes thresholds
        output_path: Path to save the plot
    """
    logger.info("Creating cumulative XXX Adult visits chart...")

    apply_plot_style()

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Left: Days thresholds
    ax1 = axes[0]
    for i, n in enumerate([1, 2, 3, 4, 5]):
        subset = cumulative_days_df[cumulative_days_df['threshold'] == n]
        ax1.plot(subset['date'], subset['share_of_all'],
                 label=f'{n}+ days', color=COLOR_PALETTE[i], linewidth=2)

    ax1.set_xlabel('Date')
    ax1.set_ylabel('Share of All Persons (%)')
    ax1.set_title('Share with at least N days of XXX Adult visits')
    ax1.legend(loc='upper left')
    ax1.tick_params(axis='x', rotation=45)

    # Right: Minutes thresholds
    ax2 = axes[1]
    minute_labels = {10: '10+ min', 30: '30+ min', 60: '1+ hr', 120: '2+ hr', 300: '5+ hr'}
    for i, n in enumerate([10, 30, 60, 120, 300]):
        subset = cumulative_minutes_df[cumulative_minutes_df['threshold_minutes'] == n]
        ax2.plot(subset['date'], subset['share_of_all'],
                 label=minute_labels[n], color=COLOR_PALETTE[i], linewidth=2)

    ax2.set_xlabel('Date')
    ax2.set_ylabel('Share of All Persons (%)')
    ax2.set_title('Share with at least N minutes of XXX Adult visits')
    ax2.legend(loc='upper left')
    ax2.tick_params(axis='x', rotation=45)

    plt.tight_layout()

    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    logger.info(f"  Chart saved to: {output_path}")


def plot_minutes_per_visit(minutes_series, stats, output_path):
    """
    Create distribution plot for minutes per visit.

    Args:
        minutes_series: Series of minutes per visit
        stats: Dictionary of statistics
        output_path: Path to save the plot
    """
    logger.info("Creating minutes per visit distribution chart...")

    apply_plot_style()

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Left: Histogram (capped at 60 minutes for readability)
    ax1 = axes[0]
    capped = minutes_series.clip(upper=60)
    ax1.hist(capped, bins=60, color=UCHICAGO_MAROON, edgecolor='white', alpha=0.8)
    ax1.axvline(stats['median'], color='#C16622', linestyle='--', linewidth=2, label=f"Median: {stats['median']:.1f} min")
    ax1.axvline(stats['mean'], color='#8A9045', linestyle='--', linewidth=2, label=f"Mean: {stats['mean']:.1f} min")
    ax1.set_xlabel('Minutes per Visit (capped at 60)')
    ax1.set_ylabel('Number of Sessions')
    ax1.set_title('Distribution of Session Duration')
    ax1.legend()

    # Right: CDF
    ax2 = axes[1]
    sorted_mins = np.sort(minutes_series)
    cdf = np.arange(1, len(sorted_mins) + 1) / len(sorted_mins)

    # Sample for plotting (too many points otherwise)
    sample_idx = np.linspace(0, len(sorted_mins) - 1, 1000).astype(int)
    ax2.plot(sorted_mins[sample_idx], cdf[sample_idx] * 100, color=UCHICAGO_MAROON, linewidth=2)

    ax2.set_xlabel('Minutes per Visit')
    ax2.set_ylabel('Cumulative % of Sessions')
    ax2.set_title('Cumulative Distribution of Session Duration')
    ax2.set_xlim(0, 120)  # Cap x-axis at 2 hours

    # Add reference lines
    for pct, label in [(50, 'p50'), (75, 'p75'), (90, 'p90')]:
        val = stats.get(f'p{pct}', stats.get('median' if pct == 50 else f'p{pct}'))
        if pct == 50:
            val = stats['median']
        ax2.axhline(pct, color='gray', linestyle=':', alpha=0.5)
        ax2.axvline(val, color='gray', linestyle=':', alpha=0.5)

    plt.tight_layout()

    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    logger.info(f"  Chart saved to: {output_path}")


def plot_gender_visit_frequency(gender_counts, output_path):
    """
    Create paired bar plot of visit frequency by gender (excluding 0 days).

    Args:
        gender_counts: DataFrame with gender and bucket counts
        output_path: Path to save the plot
    """
    logger.info("Creating gender visit frequency chart...")

    apply_plot_style()

    fig, ax = plt.subplots(figsize=(10, 6))

    # Define bucket order (excluding 0 days)
    bucket_order = ['1 day', '2-3 days', '4-10 days', '10+ days']

    # Filter out 0 days and pivot for plotting
    filtered = gender_counts[gender_counts['bucket'] != '0 days']
    pivot = filtered.pivot(index='bucket', columns='person_gender', values='share')
    pivot = pivot.reindex(bucket_order)

    # Bar positions
    x = np.arange(len(bucket_order))
    width = 0.35

    bars1 = ax.bar(x - width/2, pivot['Male'], width, label='Male', color=UCHICAGO_MAROON)
    bars2 = ax.bar(x + width/2, pivot['Female'], width, label='Female', color='#C16622')

    ax.set_xlabel('Number of Days with XXX Adult Sessions in January')
    ax.set_ylabel('Share of Gender (%)')
    ax.set_title('XXX Adult Visit Frequency by Gender')
    ax.set_xticks(x)
    ax.set_xticklabels(bucket_order)
    ax.legend()

    # Add value labels on bars
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height:.1f}%',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=9)

    plt.tight_layout()

    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    logger.info(f"  Chart saved to: {output_path}")


def plot_male_demographics(demo_results, output_path):
    """
    Create demographic splits for male XXX Adult visitors.

    Args:
        demo_results: Dictionary of DataFrames with demographic splits
        output_path: Path to save the plot
    """
    logger.info("Creating male demographics chart...")

    apply_plot_style()

    fig, axes = plt.subplots(1, 3, figsize=(18, 7))

    bucket_order = ['1 day', '2-3 days', '4-10 days', '10+ days']

    # Age range plot
    ax1 = axes[0]
    age_data = demo_results['age_range']
    age_data = age_data[age_data['bucket'] != '0 days']
    age_order = ['18-24', '25-34', '35-44', '45-54', '55-64', '65 and Over']
    age_data = age_data[age_data['age_range'].isin(age_order)]

    # Pivot and plot
    pivot = age_data.pivot(index='bucket', columns='age_range', values='share')
    pivot = pivot.reindex(bucket_order)[age_order]

    x = np.arange(len(bucket_order))
    width = 0.12
    for i, age in enumerate(age_order):
        ax1.bar(x + i*width - width*2.5, pivot[age], width, label=age, color=COLOR_PALETTE[i % len(COLOR_PALETTE)])

    ax1.set_xlabel('Days with XXX Adult Sessions')
    ax1.set_ylabel('Share of Age Group (%)')
    ax1.set_title('By Age Range')
    ax1.set_xticks(x)
    ax1.set_xticklabels(bucket_order, rotation=45, ha='right')
    ax1.legend(fontsize=8, loc='upper right')

    # HHI plot
    ax2 = axes[1]
    hhi_data = demo_results['HHI']
    hhi_data = hhi_data[hhi_data['bucket'] != '0 days']
    # Simplify HHI labels
    hhi_order = ['HHI US: Less than 25k', 'HHI US: 25k-39.999k', 'HHI US: 40k-59.999k',
                 'HHI US: 60k-74.999k', 'HHI US: 75k-99.999k', 'HHI US: 100k-149.999k',
                 'HHI US: 150k-199.999k', 'HHI US: 200k+']
    hhi_labels = ['<25k', '25-40k', '40-60k', '60-75k', '75-100k', '100-150k', '150-200k', '200k+']
    hhi_data = hhi_data[hhi_data['HHI'].isin(hhi_order)]

    pivot = hhi_data.pivot(index='bucket', columns='HHI', values='share')
    pivot = pivot.reindex(bucket_order)
    if set(hhi_order).issubset(pivot.columns):
        pivot = pivot[hhi_order]

    width = 0.09
    for i, (hhi, label) in enumerate(zip(hhi_order, hhi_labels)):
        if hhi in pivot.columns:
            ax2.bar(x + i*width - width*3.5, pivot[hhi], width, label=label, color=COLOR_PALETTE[i % len(COLOR_PALETTE)])

    ax2.set_xlabel('Days with XXX Adult Sessions')
    ax2.set_ylabel('Share of HHI Group (%)')
    ax2.set_title('By Household Income')
    ax2.set_xticks(x)
    ax2.set_xticklabels(bucket_order, rotation=45, ha='right')
    ax2.legend(fontsize=7, loc='upper right', ncol=2)

    # Race plot
    ax3 = axes[2]
    race_data = demo_results['race']
    race_data = race_data[race_data['bucket'] != '0 days']
    race_data = race_data[race_data['person_race'].isin(['Race:Black', 'Race:Non-Black'])]

    pivot = race_data.pivot(index='bucket', columns='person_race', values='share')
    pivot = pivot.reindex(bucket_order)

    width = 0.35
    if 'Race:Black' in pivot.columns:
        ax3.bar(x - width/2, pivot['Race:Black'], width, label='Black', color=UCHICAGO_MAROON)
    if 'Race:Non-Black' in pivot.columns:
        ax3.bar(x + width/2, pivot['Race:Non-Black'], width, label='Non-Black', color='#C16622')

    ax3.set_xlabel('Days with XXX Adult Sessions')
    ax3.set_ylabel('Share of Race Group (%)')
    ax3.set_title('By Race')
    ax3.set_xticks(x)
    ax3.set_xticklabels(bucket_order, rotation=45, ha='right')
    ax3.legend()

    fig.suptitle('Male XXX Adult Visit Frequency by Demographics (Among Men)', fontsize=14, y=1.02)
    plt.tight_layout()

    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    logger.info(f"  Chart saved to: {output_path}")


def main(month_id='202201', sample_size=None):
    """
    Main function to compute and export session summary statistics.

    Args:
        month_id: Month ID string (e.g., '202201')
        sample_size: If provided, randomly sample this many rows for testing
    """
    logger.info("=" * 80)
    logger.info("SESSION SUMMARY STATISTICS")
    logger.info(f"Month: {month_id}")
    if sample_size:
        logger.info(f"SAMPLE MODE: Using {sample_size:,} rows")
    logger.info("=" * 80)

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load data
    df = load_merged_sessions(month_id)

    # Sample if requested
    if sample_size and sample_size < len(df):
        logger.info(f"Sampling {sample_size:,} rows from {len(df):,} total...")
        df = df.sample(n=sample_size, random_state=42)

    # Compute statistics
    overall_summary = compute_overall_summary(df)
    xxx_summary = compute_xxx_adult_summary(df)
    top_websites = compute_top_websites(df, top_n=50)
    top_xxx_websites, total_xxx_sessions, total_xxx_duration = compute_top_xxx_adult_websites(df, top_n=50)
    category_freq = compute_category_frequency(df)
    cumulative_days, cumulative_minutes = compute_cumulative_xxx_visits(df)
    minutes_series, minutes_stats = compute_minutes_per_visit(df)
    gender_counts, person_visits = compute_gender_visit_frequency(df)
    demo_results, male_visits = compute_male_demographics(df)

    # New analyses (Issue #9)
    daily_time_stats = compute_daily_time_online(df)
    machine_persons_df, machine_sharing_dist = compute_machine_person_sharing(df)
    session_length_websites, session_length_categories = compute_session_length_stats(df, top_n=30)
    overlap_matrix = compute_website_overlap_matrix(df, top_n=5)

    # Create summary table
    summary_table = create_summary_table(overall_summary, xxx_summary)

    # Export data files
    summary_path = OUTPUT_DIR / f'session_summary_{month_id}.csv'
    summary_table.to_csv(summary_path, index=False)
    logger.info(f"\nSummary table saved to: {summary_path}")

    websites_path = OUTPUT_DIR / f'top_websites_{month_id}.csv'
    top_websites.to_csv(websites_path, index=False)
    logger.info(f"Top websites saved to: {websites_path}")

    xxx_websites_path = OUTPUT_DIR / f'top_xxx_adult_websites_{month_id}.csv'
    top_xxx_websites.to_csv(xxx_websites_path, index=False)
    logger.info(f"XXX Adult website rankings saved to: {xxx_websites_path}")

    category_path = OUTPUT_DIR / f'category_frequency_{month_id}.csv'
    category_freq.to_csv(category_path, index=False)
    logger.info(f"Category frequency saved to: {category_path}")

    cumulative_days_path = OUTPUT_DIR / f'cumulative_xxx_days_{month_id}.csv'
    cumulative_days.to_csv(cumulative_days_path, index=False)
    logger.info(f"Cumulative days saved to: {cumulative_days_path}")

    cumulative_minutes_path = OUTPUT_DIR / f'cumulative_xxx_minutes_{month_id}.csv'
    cumulative_minutes.to_csv(cumulative_minutes_path, index=False)
    logger.info(f"Cumulative minutes saved to: {cumulative_minutes_path}")

    gender_path = OUTPUT_DIR / f'gender_visit_frequency_{month_id}.csv'
    gender_counts.to_csv(gender_path, index=False)
    logger.info(f"Gender frequency saved to: {gender_path}")

    # Export new analyses (Issue #9)
    daily_time_path = OUTPUT_DIR / f'daily_time_online_{month_id}.csv'
    daily_time_stats.to_csv(daily_time_path, index=False)
    logger.info(f"Daily time online saved to: {daily_time_path}")

    machine_sharing_path = OUTPUT_DIR / f'machine_person_sharing_{month_id}.csv'
    machine_sharing_dist.to_csv(machine_sharing_path, index=False)
    logger.info(f"Machine-person sharing saved to: {machine_sharing_path}")

    session_length_websites_path = OUTPUT_DIR / f'session_length_by_website_{month_id}.csv'
    session_length_websites.to_csv(session_length_websites_path, index=False)
    logger.info(f"Session length by website saved to: {session_length_websites_path}")

    session_length_categories_path = OUTPUT_DIR / f'session_length_by_category_{month_id}.csv'
    session_length_categories.to_csv(session_length_categories_path, index=False)
    logger.info(f"Session length by category saved to: {session_length_categories_path}")

    overlap_matrix_path = OUTPUT_DIR / f'website_overlap_matrix_{month_id}.csv'
    overlap_matrix.to_csv(overlap_matrix_path, index=False)
    logger.info(f"Website overlap matrix saved to: {overlap_matrix_path}")

    # Create plots
    xxx_plot_path = OUTPUT_DIR / f'top_xxx_adult_websites_{month_id}.png'
    plot_top_xxx_adult_websites(top_xxx_websites, total_xxx_sessions, total_xxx_duration, xxx_plot_path, top_n=20)

    category_plot_path = OUTPUT_DIR / f'category_frequency_{month_id}.png'
    plot_category_frequency(category_freq, category_plot_path, top_n=20)

    combined_plot_path = OUTPUT_DIR / f'websites_and_categories_{month_id}.png'
    plot_websites_and_categories(top_websites, category_freq, combined_plot_path, n_websites=10, n_categories=20)

    cumulative_plot_path = OUTPUT_DIR / f'cumulative_xxx_visits_{month_id}.png'
    plot_cumulative_xxx_visits(cumulative_days, cumulative_minutes, cumulative_plot_path)

    minutes_plot_path = OUTPUT_DIR / f'minutes_per_visit_{month_id}.png'
    plot_minutes_per_visit(minutes_series, minutes_stats, minutes_plot_path)

    gender_plot_path = OUTPUT_DIR / f'gender_visit_frequency_{month_id}.png'
    plot_gender_visit_frequency(gender_counts, gender_plot_path)

    male_demo_plot_path = OUTPUT_DIR / f'male_demographics_{month_id}.png'
    plot_male_demographics(demo_results, male_demo_plot_path)

    # Print summary table
    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY TABLE")
    logger.info("=" * 80)
    print(summary_table.to_string(index=False))

    logger.info("\n" + "=" * 80)
    logger.info("TOP 20 WEBSITES OVERALL")
    logger.info("=" * 80)
    print(top_websites.head(20)[['rank', 'top_web_name', 'category', 'session_pct']].to_string(index=False))

    logger.info("\n" + "=" * 80)
    logger.info("TOP 20 XXX ADULT WEBSITES")
    logger.info("=" * 80)
    print(top_xxx_websites.head(20).to_string(index=False))

    logger.info("\n" + "=" * 80)
    logger.info("TOP 20 CATEGORIES (by share)")
    logger.info("=" * 80)
    print(category_freq.head(20)[['rank', 'category', 'session_pct', 'duration_pct']].to_string(index=False))

    logger.info("\n" + "=" * 80)
    logger.info("MINUTES PER VISIT STATISTICS")
    logger.info("=" * 80)
    print(f"  Mean: {minutes_stats['mean']:.2f} minutes")
    print(f"  Median: {minutes_stats['median']:.2f} minutes")
    print(f"  Std: {minutes_stats['std']:.2f} minutes")
    print(f"  25th percentile: {minutes_stats['p25']:.2f} minutes")
    print(f"  75th percentile: {minutes_stats['p75']:.2f} minutes")
    print(f"  90th percentile: {minutes_stats['p90']:.2f} minutes")
    print(f"  95th percentile: {minutes_stats['p95']:.2f} minutes")

    logger.info("\n" + "=" * 80)
    logger.info("GENDER VISIT FREQUENCY")
    logger.info("=" * 80)
    print(gender_counts.pivot(index='bucket', columns='person_gender', values='share').to_string())

    # New analyses summaries (Issue #9)
    logger.info("\n" + "=" * 80)
    logger.info("DAILY TIME ONLINE (DAY-MACHINE LEVEL)")
    logger.info("=" * 80)
    print(daily_time_stats.to_string(index=False))

    logger.info("\n" + "=" * 80)
    logger.info("MACHINE-PERSON SHARING")
    logger.info("=" * 80)
    print(machine_sharing_dist.to_string(index=False))

    logger.info("\n" + "=" * 80)
    logger.info("SESSION LENGTH BY WEBSITE (TOP 30)")
    logger.info("=" * 80)
    print(session_length_websites[['rank', 'top_web_name', 'session_count', 'share_of_machines',
                                    'mean_minutes', 'median_minutes', 'p90_minutes']].to_string(index=False))

    logger.info("\n" + "=" * 80)
    logger.info("SESSION LENGTH BY CATEGORY (TOP 30)")
    logger.info("=" * 80)
    print(session_length_categories[['rank', 'category', 'session_count', 'share_of_machines',
                                      'mean_minutes', 'median_minutes', 'p90_minutes']].to_string(index=False))

    logger.info("\n" + "=" * 80)
    logger.info("WEBSITE OVERLAP MATRIX (TOP 5)")
    logger.info("=" * 80)
    print(overlap_matrix.to_string(index=False))

    logger.info("\n" + "=" * 80)
    logger.info("COMPLETE")
    logger.info("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Compute session summary statistics')
    parser.add_argument('--sample', type=int, default=None,
                        help='Sample N rows for testing (e.g., --sample 100000)')
    parser.add_argument('--month', type=str, default='202201',
                        help='Month ID (default: 202201)')
    args = parser.parse_args()

    main(month_id=args.month, sample_size=args.sample)
