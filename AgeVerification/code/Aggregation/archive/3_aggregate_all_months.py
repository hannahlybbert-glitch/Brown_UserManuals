# Author: Hannah Lybbert
# Created: 02/16/2026
# Purpose: Optimized aggregation using Two-Pass Boundary Week Detection (Option 1)

"""
Final Aggregation Script - OPTIMIZED (Cluster)
Combines all monthly intermediate session files using a two-pass approach to minimize memory usage
while correctly handling boundary weeks (weeks spanning two months)

OPTIMIZATION STRATEGY (Option 1):
- Pass 1: Lightweight scan to identify which weeks appear in multiple files (boundary weeks)
- Pass 2:
  * Non-boundary weeks: Process one file at a time, aggregate, release from memory
  * Boundary weeks: Load raw session data from all relevant files, combine, then aggregate with nunique()

Usage: python 3_aggregate_all_months_optimized.py

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
from collections import defaultdict

# DURATION THRESHOLD: Minimum session duration (in seconds) for site-specific counts
MIN_DURATION_THRESHOLD = 3  # seconds

# ----- DEMOGRAPHIC SHARE CONFIGURATION ----- #
# Age brackets applied to continuous person_age variable
# No persons under 18 in the Comscore panel, so under_18 bracket is excluded.
AGE_BINS   = [17, 24, 34, 44, 54, 64, np.inf]
AGE_LABELS = ['18_24', '25_34', '35_44', '45_54', '55_64', '65plus']

# Strings must match the actual person_HHI_USD values in the merged parquets.
# Values are stored with the "HHI USD:" prefix (e.g. "HHI USD:Less than 25,000").
HHI_MAP = {
    'under_25k':   'HHI USD:Less than 25,000',
    '25k_40k':     'HHI USD:25,000 - 39,999',
    '40k_60k':     'HHI USD:40,000 - 59,999',
    '60k_75k':     'HHI USD:60,000 - 74,999',
    '75k_100k':    'HHI USD:75,000 - 99,999',
    '100k_150k':   'HHI USD:100,000 - 149,999',
    '150k_200k':   'HHI USD:150,000 - 199,999',
    '200k_plus':   'HHI USD:200,000 or more',
}

# All demographic share columns (state/week level — same value for all 7 coarse categories)
# NOTE: share_male + share_female will NOT sum to 1 if some panelists have an unknown/other
# gender value — both indicators are 0 for those panelists, so shares reflect fractions of
# ALL panelists with that specific label, not conditional shares among known-gender panelists.
DEMO_SHARE_COLS = (
    ['share_male', 'share_female'] +
    [f'share_age_{lbl}' for lbl in AGE_LABELS] +
    ['avg_prob_child'] +
    [f'share_hhi_{lbl}' for lbl in HHI_MAP]
)


def compute_person_demographics(sessions_df):
    """
    Compute person-level demographic shares per (state, week_of_sample, week_start_date).
    Each person is counted once per state-week regardless of session count (deduplicated).
    Returns one row per state-week with columns defined in DEMO_SHARE_COLS.
    """
    unique_persons = sessions_df.drop_duplicates(
        subset=['person_id', 'state', 'week_of_sample']
    ).copy()

    group_keys = ['state', 'week_of_sample', 'week_start_date']

    # Gender indicators
    unique_persons['_is_male']   = (unique_persons['person_gender'].str.strip().str.lower() == 'male').astype(float)
    unique_persons['_is_female'] = (unique_persons['person_gender'].str.strip().str.lower() == 'female').astype(float)

    # Age bracket indicators from continuous person_age
    unique_persons['_age_bracket'] = pd.cut(
        unique_persons['person_age'], bins=AGE_BINS, labels=AGE_LABELS
    )
    for lbl in AGE_LABELS:
        unique_persons[f'_age_{lbl}'] = (unique_persons['_age_bracket'] == lbl).astype(float)

    # Children present indicator; mean = avg_prob_child (probability child is present).
    # person_children is stored as "Children:Yes" / "Children:No" in the merged parquets.
    # Extract the value after the colon and check for "yes".
    unique_persons['_has_children'] = (
        unique_persons['person_children'].str.split(':').str[-1].str.strip().str.lower() == 'yes'
    ).astype(float)

    # HHI bracket indicators
    for label, value in HHI_MAP.items():
        unique_persons[f'_hhi_{label}'] = (
            unique_persons['person_HHI_USD'].str.strip() == value
        ).astype(float)

    # Aggregate all indicators to state-week means (= shares / probabilities)
    indicator_cols = (
        ['_is_male', '_is_female'] +
        [f'_age_{lbl}' for lbl in AGE_LABELS] +
        ['_has_children'] +
        [f'_hhi_{label}' for label in HHI_MAP]
    )
    shares = unique_persons.groupby(group_keys)[indicator_cols].mean().reset_index()

    rename_map = {
        '_is_male':      'share_male',
        '_is_female':    'share_female',
        '_has_children': 'avg_prob_child',
        **{f'_age_{lbl}': f'share_age_{lbl}' for lbl in AGE_LABELS},
        **{f'_hhi_{label}': f'share_hhi_{label}' for label in HHI_MAP},
    }
    return shares.rename(columns=rename_map)

# For cluster: comment out the os.chdir line
# os.chdir(r"C:\Users\hlybbert\OneDrive - The University of Chicago\Documents\AgeVerification")

# Get the project root directory
project_root = os.getcwd()

print("="*80)
print("FINAL AGGREGATION - ALL MONTHS (OPTIMIZED)")
print("="*80)

# ----- FILE PATHS ----- #
intermediate_dir = os.path.join(project_root, "data", "Aggregation", "intermediate")
top_websites_file = os.path.join(project_root, "data", "Aggregation", "top5_xxx_websites.csv")
output_dir = os.path.join(project_root, "data", "Aggregation", "aggregated_file")
output_file = os.path.join(output_dir, "final_aggregated.csv")

# Create output directory if needed
os.makedirs(output_dir, exist_ok=True)

# ----- FIND ALL INTERMEDIATE FILES ----- #
print(f"\n[SETUP] Finding intermediate session files...")
# Search recursively through month_id subdirectories
intermediate_files = sorted(glob(os.path.join(intermediate_dir, "*", "intermediate_sessions_*.parquet")))

if len(intermediate_files) == 0:
    print(f"ERROR: No intermediate files found in {intermediate_dir}")
    print("Please run script 2 first to create intermediate files.")
    exit(1)

print(f"  Found {len(intermediate_files)} intermediate files:")
for file in intermediate_files:
    print(f"    - {os.path.basename(file)}")

# ----- LOAD TOP WEBSITES FOR COMPLETE GRID ----- #
print(f"\n[SETUP] Loading top websites for complete grid...")
top_websites = pd.read_csv(top_websites_file)
all_coarse_categories = top_websites['website_name'].tolist() + ['other_XXX_sites', 'all_other_sites']
print(f"  Coarse categories: {len(all_coarse_categories)}")
for category in all_coarse_categories:
    print(f"    - {category}")

# ==================================================================================
# PASS 1: LIGHTWEIGHT SCAN - IDENTIFY BOUNDARY WEEKS
# ==================================================================================
print("\n" + "="*80)
print("PASS 1: IDENTIFYING BOUNDARY WEEKS")
print("="*80)

# Track which files contain which weeks
week_to_files = defaultdict(list)
file_to_weeks = {}

print("\nScanning files for week ranges...")
for file in intermediate_files:
    # Read only the week_of_sample column to minimize memory
    weeks_in_file = pd.read_parquet(file, columns=['week_of_sample'])['week_of_sample'].unique()
    file_to_weeks[file] = set(weeks_in_file)

    for week in weeks_in_file:
        week_to_files[week].append(file)

    print(f"  {os.path.basename(file)}: weeks {min(weeks_in_file)} to {max(weeks_in_file)}")

# Identify boundary weeks (appear in multiple files)
boundary_weeks = {week for week, files in week_to_files.items() if len(files) > 1}
non_boundary_weeks = {week for week, files in week_to_files.items() if len(files) == 1}

print(f"\n  Total unique weeks: {len(week_to_files)}")
print(f"  Boundary weeks (span multiple months): {len(boundary_weeks)}")
print(f"  Non-boundary weeks (within single month): {len(non_boundary_weeks)}")

if len(boundary_weeks) > 0:
    print(f"\n  Boundary weeks: {sorted(boundary_weeks)}")
    print("\n  Files involved in boundary weeks:")
    for week in sorted(boundary_weeks):
        files_list = [os.path.basename(f) for f in week_to_files[week]]
        print(f"    Week {week}: {', '.join(files_list)}")

# ==================================================================================
# PASS 2: SELECTIVE LOADING AND AGGREGATION
# ==================================================================================
print("\n" + "="*80)
print("PASS 2: SELECTIVE LOADING AND AGGREGATION")
print("="*80)

# Storage for aggregated results
aggregated_results = []

# ---------------------------------------------------------------------------------
# PASS 2A: PROCESS NON-BOUNDARY WEEKS (one file at a time)
# ---------------------------------------------------------------------------------
print(f"\n[2A] Processing non-boundary weeks (one file at a time)...")

for file in intermediate_files:
    weeks_in_this_file = file_to_weeks[file]
    non_boundary_in_this_file = weeks_in_this_file & non_boundary_weeks

    if len(non_boundary_in_this_file) == 0:
        print(f"  {os.path.basename(file)}: No non-boundary weeks, skipping")
        continue

    print(f"\n  Processing {os.path.basename(file)}...")
    print(f"    Non-boundary weeks: {sorted(non_boundary_in_this_file)}")

    # Load the file
    sessions = pd.read_parquet(file)

    # Filter to only non-boundary weeks
    sessions = sessions[sessions['week_of_sample'].isin(non_boundary_in_this_file)]
    print(f"    Sessions to process: {len(sessions):,}")

    # Calculate state-week totals (all websites combined)
    state_week_totals = sessions.groupby(['state', 'week_of_sample', 'week_start_date']).agg(
        all_machine_count=('machine_id', 'nunique'),
        all_person_count=('person_id', 'nunique')
    ).reset_index()

    # Filter sessions for site-specific counts (duration > threshold)
    sessions_filtered = sessions[sessions['duration'] > MIN_DURATION_THRESHOLD].copy()

    # Calculate total duration
    aggregated = sessions.groupby(['state', 'week_of_sample', 'week_start_date', 'coarse_category']).agg(
        total_duration_seconds=('duration', 'sum')
    ).reset_index()

    # Calculate site-specific counts (from filtered data)
    site_counts = sessions_filtered.groupby(['state', 'week_of_sample', 'week_start_date', 'coarse_category']).agg(
        site_machine_count=('machine_id', 'nunique'),
        site_person_count=('person_id', 'nunique')
    ).reset_index()

    # Merge site counts into aggregated data
    aggregated = aggregated.merge(
        site_counts,
        on=['state', 'week_of_sample', 'week_start_date', 'coarse_category'],
        how='left'
    )

    # Merge state-week totals into aggregated data
    aggregated = aggregated.merge(
        state_week_totals,
        on=['state', 'week_of_sample', 'week_start_date'],
        how='left'
    )

    # Compute person-level demographic shares (deduplicates persons within state-week)
    person_demographics = compute_person_demographics(sessions)
    aggregated = aggregated.merge(
        person_demographics,
        on=['state', 'week_of_sample', 'week_start_date'],
        how='left'
    )

    # Store results
    aggregated_results.append(aggregated)
    print(f"    Aggregated rows: {len(aggregated):,}")

    # Release memory
    del sessions, sessions_filtered, aggregated, site_counts, state_week_totals, person_demographics

print(f"\n  Non-boundary weeks processed: {len(non_boundary_weeks)} weeks from {len(aggregated_results)} file chunks")

# ---------------------------------------------------------------------------------
# PASS 2B: PROCESS BOUNDARY WEEKS (load from all relevant files)
# ---------------------------------------------------------------------------------
print(f"\n[2B] Processing boundary weeks (combining across files)...")

if len(boundary_weeks) > 0:
    for week in sorted(boundary_weeks):
        files_for_this_week = week_to_files[week]
        print(f"\n  Processing week {week}...")
        print(f"    Appears in {len(files_for_this_week)} files: {[os.path.basename(f) for f in files_for_this_week]}")

        # Load this week's data from all relevant files
        week_sessions = []
        for file in files_for_this_week:
            sessions = pd.read_parquet(file)
            sessions = sessions[sessions['week_of_sample'] == week]
            week_sessions.append(sessions)
            print(f"      Loaded {len(sessions):,} sessions from {os.path.basename(file)}")

        # Combine all sessions for this week
        combined_sessions = pd.concat(week_sessions, ignore_index=True)
        print(f"    Total combined sessions for week {week}: {len(combined_sessions):,}")

        # Calculate state-week totals (all websites combined)
        # Using nunique() on combined data correctly deduplicates IDs across files
        state_week_totals = combined_sessions.groupby(['state', 'week_of_sample', 'week_start_date']).agg(
            all_machine_count=('machine_id', 'nunique'),
            all_person_count=('person_id', 'nunique')
        ).reset_index()

        # Filter sessions for site-specific counts (duration > threshold)
        sessions_filtered = combined_sessions[combined_sessions['duration'] > MIN_DURATION_THRESHOLD].copy()

        # Calculate total duration
        aggregated = combined_sessions.groupby(['state', 'week_of_sample', 'week_start_date', 'coarse_category']).agg(
            total_duration_seconds=('duration', 'sum')
        ).reset_index()

        # Calculate site-specific counts (from filtered data)
        # Using nunique() on combined filtered data correctly deduplicates IDs
        site_counts = sessions_filtered.groupby(['state', 'week_of_sample', 'week_start_date', 'coarse_category']).agg(
            site_machine_count=('machine_id', 'nunique'),
            site_person_count=('person_id', 'nunique')
        ).reset_index()

        # Merge site counts into aggregated data
        aggregated = aggregated.merge(
            site_counts,
            on=['state', 'week_of_sample', 'week_start_date', 'coarse_category'],
            how='left'
        )

        # Merge state-week totals into aggregated data
        aggregated = aggregated.merge(
            state_week_totals,
            on=['state', 'week_of_sample', 'week_start_date'],
            how='left'
        )

        # Compute person-level demographic shares (nunique() correctly deduplicates across files)
        person_demographics = compute_person_demographics(combined_sessions)
        aggregated = aggregated.merge(
            person_demographics,
            on=['state', 'week_of_sample', 'week_start_date'],
            how='left'
        )

        # Store results
        aggregated_results.append(aggregated)
        print(f"    Aggregated rows for week {week}: {len(aggregated):,}")

        # Release memory
        del week_sessions, combined_sessions, sessions_filtered, aggregated, site_counts, state_week_totals, person_demographics

else:
    print("  No boundary weeks found (all weeks fully contained within single months)")

# ==================================================================================
# COMBINE ALL AGGREGATED RESULTS
# ==================================================================================
print("\n" + "="*80)
print("COMBINING AGGREGATED RESULTS")
print("="*80)

print(f"Combining {len(aggregated_results)} aggregated chunks...")
aggregated = pd.concat(aggregated_results, ignore_index=True)
print(f"  Total aggregated rows: {len(aggregated):,}")

# Release memory
del aggregated_results

# Get all states and weeks for complete grid
all_states = sorted(aggregated['state'].unique())
all_weeks = sorted(aggregated['week_of_sample'].unique())

print(f"  States: {len(all_states)}")
print(f"  Weeks: {len(all_weeks)} (week {min(all_weeks)} to week {max(all_weeks)})")

# Create week_of_sample to week_start_date mapping
week_date_map = aggregated[['week_of_sample', 'week_start_date']].drop_duplicates().set_index('week_of_sample')['week_start_date'].to_dict()

# ==================================================================================
# CREATE COMPLETE GRID
# ==================================================================================
print("\n" + "="*80)
print("CREATING COMPLETE GRID")
print("="*80)

print("Creating complete grid for all state-week-category combinations...")
complete_grid = pd.DataFrame(
    list(product(all_states, all_weeks, all_coarse_categories)),
    columns=['state', 'week_of_sample', 'coarse_category']
)

# Add week_start_date to complete grid
complete_grid['week_start_date'] = complete_grid['week_of_sample'].map(week_date_map)

print(f"  Complete grid: {len(complete_grid):,} rows")
print(f"    ({len(all_states)} states × {len(all_weeks)} weeks × {len(all_coarse_categories)} categories)")

# Merge aggregated data with complete grid
aggregated = complete_grid.merge(
    aggregated,
    on=['state', 'week_of_sample', 'week_start_date', 'coarse_category'],
    how='left'
)

# Fill missing values with 0 for site-level and duration columns
aggregated['total_duration_seconds'] = aggregated['total_duration_seconds'].fillna(0)
aggregated['site_machine_count'] = aggregated['site_machine_count'].fillna(0)
aggregated['site_person_count'] = aggregated['site_person_count'].fillna(0)

# Fix: propagate all state-week-level columns across all 7 coarse categories.
# After the complete-grid LEFT merge, categories with no sessions in a state-week get
# NaN for all_machine_count and demographic shares. These are state-week-level quantities
# (identical for all 7 categories), so we broadcast from whichever categories had sessions.
# Type A state-weeks (no data at all) remain 0 / NaN after the fillna below.
state_week_level_cols = ['all_machine_count', 'all_person_count'] + DEMO_SHARE_COLS
state_week_corrected = (
    aggregated[aggregated['all_machine_count'] > 0]
    .groupby(['state', 'week_of_sample'])[state_week_level_cols]
    .first()
    .reset_index()
)
aggregated = aggregated.drop(columns=state_week_level_cols)
aggregated = aggregated.merge(state_week_corrected, on=['state', 'week_of_sample'], how='left')
# State-weeks with no data at all (Type A): counts get 0, shares get NaN (no population to describe)
aggregated['all_machine_count'] = aggregated['all_machine_count'].fillna(0)
aggregated['all_person_count']  = aggregated['all_person_count'].fillna(0)
# Demographic share columns remain NaN for empty state-weeks (correct — no panelists observed)

print(f"  Aggregated rows after grid: {len(aggregated):,}")

# ==================================================================================
# CALCULATE LOG METRICS
# ==================================================================================
print("\n" + "="*80)
print("CALCULATING LOG METRICS")
print("="*80)

# hrs_per_machine = total_duration_seconds / (all_machine_count * 3600)  [level]
aggregated['hrs_per_machine'] = np.where(
    (aggregated['total_duration_seconds'] > 0) & (aggregated['all_machine_count'] > 0),
    aggregated['total_duration_seconds'] / (aggregated['all_machine_count'] * 3600),
    np.nan
)

# hrs_per_person = total_duration_seconds / (all_person_count * 3600)  [level]
aggregated['hrs_per_person'] = np.where(
    (aggregated['total_duration_seconds'] > 0) & (aggregated['all_person_count'] > 0),
    aggregated['total_duration_seconds'] / (aggregated['all_person_count'] * 3600),
    np.nan
)

# log_hrs_per_machine = ln(hrs_per_machine)
aggregated['log_hrs_per_machine'] = np.where(
    aggregated['hrs_per_machine'].notna(),
    np.log(aggregated['hrs_per_machine']),
    np.nan
)

# log_hrs_per_person = ln(hrs_per_person)
aggregated['log_hrs_per_person'] = np.where(
    aggregated['hrs_per_person'].notna(),
    np.log(aggregated['hrs_per_person']),
    np.nan
)

print("  Calculated hrs_per_machine, hrs_per_person, log_hrs_per_machine, log_hrs_per_person")

# ==================================================================================
# SORT AND REORDER COLUMNS
# ==================================================================================
aggregated = aggregated.sort_values(['state', 'week_of_sample', 'coarse_category'])

column_order = [
    'state',
    'week_of_sample',
    'week_start_date',
    'coarse_category',
    'all_machine_count',
    'all_person_count',
    'site_machine_count',
    'site_person_count',
    'total_duration_seconds',
    'hrs_per_machine',
    'hrs_per_person',
    'log_hrs_per_machine',
    'log_hrs_per_person',
    # Person-level demographic shares (state/week level — same for all 7 categories)
    'share_male',
    'share_female',
    'share_age_18_24',
    'share_age_25_34',
    'share_age_35_44',
    'share_age_45_54',
    'share_age_55_64',
    'share_age_65plus',
    'avg_prob_child',
    'share_hhi_under_25k',
    'share_hhi_25k_40k',
    'share_hhi_40k_60k',
    'share_hhi_60k_75k',
    'share_hhi_75k_100k',
    'share_hhi_100k_150k',
    'share_hhi_150k_200k',
    'share_hhi_200k_plus',
]
aggregated = aggregated[column_order]

# ==================================================================================
# DISPLAY SUMMARY
# ==================================================================================
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

# ==================================================================================
# SUMMARY BY COARSE CATEGORY
# ==================================================================================
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

# ==================================================================================
# SAVE OUTPUT
# ==================================================================================
print("\n" + "="*80)
print(f"Saving to {output_file}...")
aggregated.to_csv(output_file, index=False)

print("\n" + "="*80)
print("COMPLETE")
print("="*80)
print(f"Final output saved to: {output_file}")
print(f"Total rows: {len(aggregated):,}")
print("="*80)
