# Author: Hannah Lybbert
# Created: 02/11/2026
# Purpoose: Aggregate web browsing data by state, week, and website category for testing

"""
Test Aggregation Script
Aggregates web browsing data by state, week, and website category
Tests with January 2022 and February 2022 data

Output: State-week-website level aggregates
- Top 5 XXX Adult sites (by total duration)
- Other XXX sites
- All other websites
"""

import pandas as pd
import numpy as np
import os
import sys

# SAMPLE_SIZE: Set to None for full data, or a number (e.g., 100000) for testing
SAMPLE_SIZE = 100000 if len(sys.argv) == 1 else (None if sys.argv[1] == 'full' else int(sys.argv[1]))

# DURATION THRESHOLD: Minimum session duration (in seconds) for site-specific counts
MIN_DURATION_THRESHOLD = 3  # seconds


# For cluster: comment out the os.chdir line
os.chdir(r"C:\Users\hlybbert\OneDrive - The University of Chicago\Documents\AgeVerification")

# Get the project root directory
project_root = os.getcwd()

# File paths
sessions_file = os.path.join(project_root, "data", "ProcessComscore", "merged_session_files", "merged_sessions_202201.parquet")

# Check for both .txt (local) and .txt.gz (cluster) versions
time_lookup_base = os.path.join(project_root, "raw", "Lookups", "time_lookup", "comscore_time_lookup_202201.txt")
if os.path.exists(time_lookup_base):
    time_lookup_file = time_lookup_base
elif os.path.exists(time_lookup_base + ".gz"):
    time_lookup_file = time_lookup_base + ".gz"
else:
    raise FileNotFoundError(f"Could not find time lookup file at {time_lookup_base} or {time_lookup_base}.gz")

output_dir = os.path.join(project_root, "data", "ProcessAuxiliary", "Aggregation")

# Output filename depends on whether this is a sample or full run
if SAMPLE_SIZE:
    output_file = os.path.join(output_dir, f"test_aggregated_202201_sample{SAMPLE_SIZE}.csv")
else:
    output_file = os.path.join(output_dir, "test_aggregated_202201.csv")

# Create output directory if needed
os.makedirs(output_dir, exist_ok=True)

if SAMPLE_SIZE:
    print(f"Loading SAMPLE of {SAMPLE_SIZE:,} sessions for testing...")
    print("(Run with 'full' argument for complete dataset)")
else:
    print("Loading FULL sessions data...")

# Read only necessary columns to reduce memory usage
columns_to_read = ['person_id', 'time_id', 'duration', 'top_web_name', 'subcategory', 'state']
sessions = pd.read_parquet(sessions_file, columns=columns_to_read)
if SAMPLE_SIZE:
    sessions = sessions.head(SAMPLE_SIZE)
print(f"Loaded {len(sessions):,} sessions")

print("\nLoading time lookup...")
# Read time lookup file (no header)
time_lookup = pd.read_csv(
    time_lookup_file,
    sep='\t',
    header=None,
    names=['time_id', 'week_id', 'unknown', 'date']
)
print(f"Loaded {len(time_lookup):,} days")

# Merge sessions with time lookup to get date information
print("\nMerging sessions with time lookup...")
sessions = sessions.merge(time_lookup[['time_id', 'date']], on='time_id', how='left')

# Filter out sessions with zero or missing duration
sessions = sessions[sessions['duration'] > 0].copy()
print(f"After filtering zero duration: {len(sessions):,} sessions")

# Create week_of_sample using alternative approach: floor(days / 7)
# Use FIXED baseline across all months for consistent week numbering
print("\nCreating week_of_sample variable...")

# Fixed base date for entire sample period (start of January 2022)
base_date = pd.to_datetime('2022-01-01')

# Look up the day_index (time_id) for this base date from time lookup
time_lookup['date_parsed'] = pd.to_datetime(time_lookup['date'])

# Try to find the base_date in the current month's time_lookup
# If not present (e.g., for Feb data), we'll still use the fixed base_date
base_date_rows = time_lookup[time_lookup['date_parsed'] == base_date]
if len(base_date_rows) > 0:
    starting_day_index = base_date_rows.iloc[0]['time_id']
    print(f"Base date: {base_date.strftime('%Y-%m-%d')} (day index: {starting_day_index})")
else:
    # For months after January, estimate day_index based on first day of current month
    first_day_of_month = time_lookup['date_parsed'].min()
    days_from_base = (first_day_of_month - base_date).days
    starting_day_index = time_lookup['time_id'].min() - days_from_base
    print(f"Base date: {base_date.strftime('%Y-%m-%d')} (estimated day index: {starting_day_index})")
    print(f"First day in current month: {first_day_of_month.strftime('%Y-%m-%d')}")

# Calculate week_of_sample (consistent across all months)
sessions['date_parsed'] = pd.to_datetime(sessions['date'])
sessions['days_since_base'] = (sessions['date_parsed'] - base_date).dt.days
sessions['week_of_sample'] = sessions['days_since_base'] // 7 + 1

print(f"Week range in this data: {sessions['week_of_sample'].min()} to {sessions['week_of_sample'].max()}")
print(f"Unique weeks: {sessions['week_of_sample'].nunique()}")

# Identify top 5 XXX Adult websites by total duration
print("\nIdentifying top 5 XXX Adult websites...")
xxx_adult_sessions = sessions[sessions['subcategory'] == 'XXX Adult'].copy()
print(f"Found {len(xxx_adult_sessions):,} XXX Adult sessions")

# Calculate total duration per website
website_totals = xxx_adult_sessions.groupby('top_web_name')['duration'].sum().sort_values(ascending=False)
print(f"\nTop 10 XXX Adult websites by total duration:")
for i, (website, duration) in enumerate(website_totals.head(10).items(), 1):
    print(f"{i:2d}. {website:30s} {duration:12,.0f} seconds ({duration/3600:,.1f} hours)")

top_5_websites = website_totals.head(5).index.tolist()
print(f"\nTop 5 websites selected: {top_5_websites}")

# Select one random XXX Adult website that is NOT in the top 5
non_top_5_websites = website_totals[~website_totals.index.isin(top_5_websites)]
if len(non_top_5_websites) > 0:
    # Use a fixed random seed for reproducibility
    np.random.seed(42)
    random_xxx_website = np.random.choice(non_top_5_websites.index)
    print(f"\nRandom non-top-5 XXX Adult website selected: {random_xxx_website}")
else:
    random_xxx_website = None
    print("\nWarning: No non-top-5 XXX Adult websites found")

# Create website category column
def assign_website_category(row):
    """Assign each session to one of 7 categories:
    - Top 5 XXX Adult websites (by actual name)
    - One random non-top-5 XXX Adult website (by actual name)
    - All other sites
    """
    if row['subcategory'] == 'XXX Adult':
        if row['top_web_name'] in top_5_websites:
            # Return the website name for top 5
            return row['top_web_name']
        elif random_xxx_website and row['top_web_name'] == random_xxx_website:
            # Return the random website name
            return row['top_web_name']
        else:
            # All other XXX sites are grouped into 'all_other_sites'
            return 'all_other_sites'
    else:
        return 'all_other_sites'

print("\nAssigning website categories...")
sessions['website_category'] = sessions.apply(assign_website_category, axis=1)

# Verify categories
print("\nWebsite category distribution:")
print(sessions['website_category'].value_counts())

# Step 1: Calculate state-week totals (ALL websites combined)
print("\n[Aggregation Step 1/3] Calculating state-week totals...")
state_week_totals = sessions.groupby(['state', 'week_of_sample']).agg(
    all_machine_count=('machine_id', 'nunique'),
    all_person_count=('person_id', 'nunique')
).reset_index()

print(f"  State-week combinations: {len(state_week_totals):,}")

# Step 2: Filter sessions for site-specific counts (duration > threshold)
print(f"\n[Aggregation Step 2/3] Filtering sessions with duration > {MIN_DURATION_THRESHOLD} seconds for site counts...")
sessions_filtered = sessions[sessions['duration'] > MIN_DURATION_THRESHOLD].copy()
print(f"  Sessions after duration filter: {len(sessions_filtered):,} ({(len(sessions_filtered)/len(sessions))*100:.1f}% of total)")

# Step 3: Aggregate by state, week, and website category
print("\n[Aggregation Step 3/3] Aggregating by state, week, and website...")
aggregated = sessions.groupby(['state', 'week_of_sample', 'website_category']).agg(
    total_duration_seconds=('duration', 'sum')
).reset_index()

# Calculate site-specific counts (from filtered data)
site_counts = sessions_filtered.groupby(['state', 'week_of_sample', 'website_category']).agg(
    site_machine_count=('machine_id', 'nunique'),
    site_person_count=('person_id', 'nunique')
).reset_index()

# Merge site counts into aggregated data
aggregated = aggregated.merge(
    site_counts,
    on=['state', 'week_of_sample', 'website_category'],
    how='left'
)

# Merge state-week totals into aggregated data
aggregated = aggregated.merge(
    state_week_totals,
    on=['state', 'week_of_sample'],
    how='left'
)

# Create complete grid of all state × week × website_category combinations
print("\nCreating complete grid for all state-week-website combinations...")
all_states = sorted(sessions['state'].unique())
all_weeks = sorted(sessions['week_of_sample'].unique())
all_website_categories = top_5_websites + [random_xxx_website] + ['all_other_sites']

# Create a dataframe with all possible combinations
from itertools import product
complete_grid = pd.DataFrame(
    list(product(all_states, all_weeks, all_website_categories)),
    columns=['state', 'week_of_sample', 'website_category']
)

print(f"Complete grid: {len(complete_grid):,} rows ({len(all_states)} states × {len(all_weeks)} weeks × {len(all_website_categories)} categories)")

# Merge aggregated data with complete grid
aggregated = complete_grid.merge(
    aggregated,
    on=['state', 'week_of_sample', 'website_category'],
    how='left'
)

# Fill missing values with 0
aggregated['total_duration_seconds'] = aggregated['total_duration_seconds'].fillna(0)
aggregated['site_machine_count'] = aggregated['site_machine_count'].fillna(0)
aggregated['site_person_count'] = aggregated['site_person_count'].fillna(0)

# Note: all_machine_count and all_person_count should not have missing values for real state-weeks
# but may have NaN for complete grid rows that don't exist in data
# We'll handle this when calculating log metrics

# Calculate log metrics
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

# For rows with no data (complete grid placeholders), fill all counts with 0
aggregated['all_machine_count'] = aggregated['all_machine_count'].fillna(0)
aggregated['all_person_count'] = aggregated['all_person_count'].fillna(0)

# Sort by state, week, and website category
aggregated = aggregated.sort_values(['state', 'week_of_sample', 'website_category'])

print(f"\nFinal aggregated data: {len(aggregated):,} rows")
print(f"({len(all_states)} states × {len(all_weeks)} weeks × {len(all_website_categories)} categories = {len(all_states) * len(all_weeks) * len(all_website_categories)} expected)")

# Reorder columns for clarity
column_order = [
    'state',
    'week_of_sample',
    'website_category',
    'all_machine_count',
    'all_person_count',
    'site_machine_count',
    'site_person_count',
    'total_duration_seconds',
    'log_hrs_per_machine',
    'log_hrs_per_person'
]
aggregated = aggregated[column_order]

# Display sample of results
print("\nSample of aggregated data:")
print(aggregated.head(15).to_string(index=False))

# Display statistics
print("\nSummary statistics:")
print(aggregated[['total_duration_seconds', 'site_machine_count', 'site_person_count',
                   'all_machine_count', 'all_person_count',
                   'log_hrs_per_machine', 'log_hrs_per_person']].describe())

# Save to CSV
print(f"\nSaving to {output_file}...")
aggregated.to_csv(output_file, index=False)
print("Done!")

# Print summary by website category
print("\n" + "="*80)
print("Summary by website category:")
print("="*80)
category_summary = aggregated.groupby('website_category').agg({
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
