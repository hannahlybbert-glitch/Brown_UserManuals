# Author: Hannah Lybbert
# Created: 02/11/2026
# Purpose: Aggregate all intermediate session files into final state-week-category dataset

"""
Final Aggregation Script (Cluster)
Combines all monthly intermediate session files and aggregates to state-week-category level
Handles boundary week deduplication (weeks spanning two months)

Usage: python 3_aggregate_all_months.py

Input:
- intermediate_sessions_YYYYMM.parquet files (all months)
- top5_xxx_websites.csv (for complete grid)

Output:
- final_aggregated.csv (54,600 rows: 50 states × 156 weeks × 7 coarse categories)

Coarse Categories (7 total):
- Top 5 XXX Adult websites (by name) - tracked consistently across all months
- other_XXX_sites - All other XXX Adult websites not in top 5 (pooled, varies by month)
- all_other_sites - All non-XXX websites
"""

import pandas as pd
import numpy as np
import os
from glob import glob
from itertools import product

# DURATION THRESHOLD: Minimum session duration (in seconds) for site-specific counts
MIN_DURATION_THRESHOLD = 3  # seconds

# For cluster: comment out the os.chdir line
# os.chdir(r"C:\Users\hlybbert\OneDrive - The University of`` Chicago\Documents\AgeVerification")

# Get the project root directory
project_root = os.getcwd()

print("="*80)
print("FINAL AGGREGATION - ALL MONTHS")
print("="*80)

# ----- FILE PATHS ----- #
intermediate_dir = os.path.join(project_root, "data", "Aggregation", "intermediate")
top_websites_file = os.path.join(project_root, "data", "Aggregation", "top5_xxx_websites.csv")
output_dir = os.path.join(project_root, "data", "Aggregation", "aggregated_file")
output_file = os.path.join(output_dir, "final_aggregated.csv")

# Create output directory if needed
os.makedirs(output_dir, exist_ok=True)

# ----- LOAD ALL INTERMEDIATE FILES ----- #
print(f"\n[1/5] Loading all intermediate session files...")
# Search recursively through month_id subdirectories
intermediate_files = sorted(glob(os.path.join(intermediate_dir, "*", "intermediate_sessions_*.parquet")))

if len(intermediate_files) == 0:
    print(f"ERROR: No intermediate files found in {intermediate_dir}")
    print("Please run script 2 first to create intermediate files.")
    exit(1)

print(f"  Found {len(intermediate_files)} intermediate files:")
for file in intermediate_files:
    print(f"    - {os.path.basename(file)}")

# Load and combine all sessions
all_sessions = []
for file in intermediate_files:
    sessions = pd.read_parquet(file)
    all_sessions.append(sessions)
    print(f"  Loaded {len(sessions):,} sessions from {os.path.basename(file)}")

sessions = pd.concat(all_sessions, ignore_index=True)
print(f"\n  Total combined sessions: {len(sessions):,}")
print(f"  Week range: {sessions['week_of_sample'].min()} to {sessions['week_of_sample'].max()}")
print(f"  Unique weeks: {sessions['week_of_sample'].nunique()}")
print(f"  Unique states: {sessions['state'].nunique()}")

# ----- LOAD TOP WEBSITES FOR COMPLETE GRID ----- #
print(f"\n[2/5] Loading top websites for complete grid...")
top_websites = pd.read_csv(top_websites_file)
all_coarse_categories = top_websites['website_name'].tolist() + ['other_XXX_sites', 'all_other_sites']
print(f"  Coarse categories: {len(all_coarse_categories)}")
for category in all_coarse_categories:
    print(f"    - {category}")

# ----- CALCULATE STATE-WEEK TOTALS ----- #
print(f"\n[3/5] Calculating state-week totals (all websites combined)...")
state_week_totals = sessions.groupby(['state', 'week_of_sample']).agg(
    all_machine_count=('machine_id', 'nunique'),
    all_person_count=('person_id', 'nunique')
).reset_index()

print(f"  State-week combinations: {len(state_week_totals):,}")

# ----- FILTER SESSIONS FOR SITE-SPECIFIC COUNTS ----- #
print(f"\n[4/5] Filtering sessions with duration > {MIN_DURATION_THRESHOLD} seconds for site counts...")
sessions_filtered = sessions[sessions['duration'] > MIN_DURATION_THRESHOLD].copy()
print(f"  Sessions after duration filter: {len(sessions_filtered):,} ({(len(sessions_filtered)/len(sessions))*100:.1f}% of total)")

# ----- AGGREGATE BY STATE, WEEK, AND COARSE CATEGORY ----- #
print(f"\n[5/5] Aggregating by state, week, and coarse category...")

# Calculate total duration
print("  Calculating total duration...")
aggregated = sessions.groupby(['state', 'week_of_sample', 'coarse_category']).agg(
    total_duration_seconds=('duration', 'sum')
).reset_index()

# Calculate site-specific counts (from filtered data)
print("  Calculating site-specific machine and person counts...")
site_counts = sessions_filtered.groupby(['state', 'week_of_sample', 'coarse_category']).agg(
    site_machine_count=('machine_id', 'nunique'),
    site_person_count=('person_id', 'nunique')
).reset_index()

# Merge site counts into aggregated data
aggregated = aggregated.merge(
    site_counts,
    on=['state', 'week_of_sample', 'coarse_category'],
    how='left'
)

# Merge state-week totals into aggregated data
aggregated = aggregated.merge(
    state_week_totals,
    on=['state', 'week_of_sample'],
    how='left'
)

print(f"  Aggregated rows before grid: {len(aggregated):,}")

# ----- CREATE COMPLETE GRID ----- #
print("\nCreating complete grid for all state-week-website combinations...")
all_states = sorted(sessions['state'].unique())
all_weeks = sorted(sessions['week_of_sample'].unique())

# Create complete grid
complete_grid = pd.DataFrame(
    list(product(all_states, all_weeks, all_coarse_categories)),
    columns=['state', 'week_of_sample', 'coarse_category']
)

print(f"  Complete grid: {len(complete_grid):,} rows")
print(f"    ({len(all_states)} states × {len(all_weeks)} weeks × {len(all_coarse_categories)} categories)")

# Merge aggregated data with complete grid
aggregated = complete_grid.merge(
    aggregated,
    on=['state', 'week_of_sample', 'coarse_category'],
    how='left'
)

# Fill missing values with 0
aggregated['total_duration_seconds'] = aggregated['total_duration_seconds'].fillna(0)
aggregated['site_machine_count'] = aggregated['site_machine_count'].fillna(0)
aggregated['site_person_count'] = aggregated['site_person_count'].fillna(0)

# For rows with no data (complete grid placeholders), fill all counts with 0
aggregated['all_machine_count'] = aggregated['all_machine_count'].fillna(0)
aggregated['all_person_count'] = aggregated['all_person_count'].fillna(0)

print(f"  Aggregated rows after grid: {len(aggregated):,}")

# ----- CALCULATE LOG METRICS ----- #
print("\nCalculating log metrics...")

# log_hrs_per_machine = ln(total_duration_seconds / (all_machine_count * 3600))
aggregated['log_hrs_per_machine'] = np.where(
    (aggregated['total_duration_seconds'] > 0) & (aggregated['all_machine_count'] > 0),
    np.log(aggregated['total_duration_seconds'] / (aggregated['all_machine_count'] * 3600)),
    np.nan
)

# log_hrs_per_person = ln(total_duration_seconds / (all_person_count * 3600))
aggregated['log_hrs_per_person'] = np.where(
    (aggregated['total_duration_seconds'] > 0) & (aggregated['all_person_count'] > 0),
    np.log(aggregated['total_duration_seconds'] / (aggregated['all_person_count'] * 3600)),
    np.nan
)

# ----- SORT AND REORDER COLUMNS ----- #
aggregated = aggregated.sort_values(['state', 'week_of_sample', 'coarse_category'])

column_order = [
    'state',
    'week_of_sample',
    'coarse_category',
    'all_machine_count',
    'all_person_count',
    'site_machine_count',
    'site_person_count',
    'total_duration_seconds',
    'log_hrs_per_machine',
    'log_hrs_per_person'
]
aggregated = aggregated[column_order]

# ----- DISPLAY SUMMARY ----- #
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Final aggregated data: {len(aggregated):,} rows")
print(f"  States: {len(all_states)}")
print(f"  Weeks: {len(all_weeks)} (week {min(all_weeks)} to week {max(all_weeks)})")
print(f"  Website categories: {len(all_coarse_categories)}")
print(f"  Expected rows: {len(all_states) * len(all_weeks) * len(all_coarse_categories):,}")

print("\nSummary statistics:")
print(aggregated[['total_duration_seconds', 'site_machine_count', 'site_person_count',
                   'all_machine_count', 'all_person_count',
                   'log_hrs_per_machine', 'log_hrs_per_person']].describe())

# ----- SUMMARY BY COARSE CATEGORY ----- #
print("\n" + "="*80)
print("Summary by coarse category:")
print("="*80)
category_summary = aggregated.groupby('coarse_category').agg({
    'total_duration_seconds': 'sum',
    'site_machine_count': 'sum',
    'site_person_count': 'sum',
    'log_hrs_per_machine': 'mean',
    'log_hrs_per_person': 'mean'
}).sort_values('total_duration_seconds', ascending=False)

for category in category_summary.index:
    row = category_summary.loc[category]
    print(f"\n{category}:")
    print(f"  Total duration: {row['total_duration_seconds']:,.0f} seconds ({row['total_duration_seconds']/3600:,.1f} hours)")
    print(f"  Total site machines (summed): {row['site_machine_count']:,.0f}")
    print(f"  Total site persons (summed): {row['site_person_count']:,.0f}")
    print(f"  Mean log_hrs_per_machine: {row['log_hrs_per_machine']:.4f}")
    print(f"  Mean log_hrs_per_person: {row['log_hrs_per_person']:.4f}")

# ----- SAVE OUTPUT ----- #
print("\n" + "="*80)
print(f"Saving to {output_file}...")
aggregated.to_csv(output_file, index=False)

print("\n" + "="*80)
print("COMPLETE")
print("="*80)
print(f"Final output saved to: {output_file}")
print(f"Total rows: {len(aggregated):,}")
print("="*80)
