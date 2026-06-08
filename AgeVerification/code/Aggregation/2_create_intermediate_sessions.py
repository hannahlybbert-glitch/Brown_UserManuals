# Author: Hannah Lybbert
# Created: 02/11/2026
# Purpose: Create intermediate session-level files with week_of_sample and coarse_category

"""
Create Intermediate Session Files (Per Month)
Processes one month at a time, adding week_of_sample and coarse_category to session data
Outputs SESSION-LEVEL data (not aggregated) for final aggregation script

Usage: python 2_create_intermediate_sessions.py YYYYMM
Example: python 2_create_intermediate_sessions.py 202201

Input:
- merged_sessions_YYYYMM.parquet
- top5_xxx_websites.csv (from script 1)
- comscore_time_lookup_YYYYMM.txt

Output:
- intermediate_sessions_YYYYMM.parquet (session-level with week and coarse category)

Coarse Categories (9 total):
- Top 5 XXX Adult websites (by name) - tracked consistently across all months
- other_XXX_sites - All other XXX Adult websites not in top 5 (pooled, varies by month)
- VPNclean - Top 3 pure VPN providers (NordVPN, ExpressVPN, Surfshark)
- allVPN - All other whitelisted VPN sites (priority: XXX Adult > VPNclean > allVPN > all_other_sites)
- all_other_sites - All non-XXX, non-VPN websites
"""

import pandas as pd
import numpy as np
import os
import sys

# For cluster: comment out the os.chdir line
# os.chdir(r"C:\Users\hlybbert\OneDrive - The University of Chicago\Documents\AgeVerification")

# Get the project root directory
project_root = os.getcwd()

# ----- COMMAND LINE ARGUMENTS ----- #
if len(sys.argv) != 2:
    print("Usage: python 2_create_intermediate_sessions.py YYYYMM")
    print("Example: python 2_create_intermediate_sessions.py 202201")
    sys.exit(1)

yyyymm = sys.argv[1]

print("="*80)
print(f"CREATING INTERMEDIATE SESSIONS FOR {yyyymm}")
print("="*80)

# ----- FILE PATHS ----- #
sessions_file = os.path.join(project_root, "data", "ProcessComscore", "merged_session_files", f"merged_sessions_{yyyymm}.parquet")
top_websites_file = os.path.join(project_root, "data", "Aggregation", "top5_xxx_websites.csv")

# Check for both .txt (local) and .txt.gz (cluster) versions
time_lookup_base = os.path.join(project_root, "raw", "Lookups", "time_lookup", f"comscore_time_lookup_{yyyymm}.txt")
if os.path.exists(time_lookup_base):
    time_lookup_file = time_lookup_base
elif os.path.exists(time_lookup_base + ".gz"):
    time_lookup_file = time_lookup_base + ".gz"
else:
    raise FileNotFoundError(f"Could not find time lookup file at {time_lookup_base} or {time_lookup_base}.gz")

# ----- LOAD DATA ----- #
print(f"\n[1/5] Loading sessions for {yyyymm}...")
columns_to_read = [
    'machine_id', 'time_id', 'duration', 'top_web_name', 'subcategory', 'month_id', 'vpn_site', 'vpn_clean_site',
]
sessions = pd.read_parquet(sessions_file, columns=columns_to_read)
print(f"  Loaded {len(sessions):,} sessions")

# Get month_id for output directory
month_id = sessions['month_id'].iloc[0]
print(f"  Month ID: {month_id}")

# Set up output paths using month_id
output_dir = os.path.join(project_root, "data", "Aggregation", "intermediate", str(month_id))
output_file = os.path.join(output_dir, f"intermediate_sessions_{yyyymm}.parquet")

# Create output directory if needed
os.makedirs(output_dir, exist_ok=True)

print(f"\n[2/5] Loading top 5 XXX Adult websites (from January 2022)...")
top_websites = pd.read_csv(top_websites_file)
top_5_websites = top_websites['website_name'].tolist()

print(f"  Top 5 websites: {top_5_websites}")

print(f"\n[3/5] Loading time lookup for {yyyymm}...")
time_lookup = pd.read_csv(
    time_lookup_file,
    sep='\t',
    header=None,
    names=['time_id', 'week_id', 'unknown', 'date']
)
print(f"  Loaded {len(time_lookup):,} days")

# ----- MERGE TIME INFORMATION ----- #
print("\n[4/5] Merging sessions with time lookup...")
sessions = sessions.merge(time_lookup[['time_id', 'date']], on='time_id', how='left')

# Filter out sessions with zero or missing duration
sessions_before_filter = len(sessions)
sessions = sessions[sessions['duration'] > 0].copy()
print(f"  After filtering zero duration: {len(sessions):,} sessions ({(len(sessions)/sessions_before_filter)*100:.1f}% retained)")

# Winsorize duration at 95th percentile
p95_duration = sessions['duration'].quantile(0.95)
sessions['duration'] = sessions['duration'].clip(upper=p95_duration)
print(f"  Winsorized duration at 95th percentile: {p95_duration:.1f}")

# ----- CREATE WEEK_OF_SAMPLE VARIABLE ----- #
print("\n[5/5] Creating week_of_sample variable...")

# Fixed base date for entire sample period (start of January 2022)
base_date = pd.to_datetime('2022-01-01')

# Parse dates and calculate week_of_sample
sessions['date_parsed'] = pd.to_datetime(sessions['date'])
sessions['days_since_base'] = (sessions['date_parsed'] - base_date).dt.days
sessions['week_of_sample'] = sessions['days_since_base'] // 7 + 1

print(f"  Base date: {base_date.strftime('%Y-%m-%d')}")
print(f"  Week range in {yyyymm}: {sessions['week_of_sample'].min()} to {sessions['week_of_sample'].max()}")
print(f"  Date range: {sessions['date_parsed'].min().date()} to {sessions['date_parsed'].max().date()}")
print(f"  Unique weeks: {sessions['week_of_sample'].nunique()}")

# ----- ASSIGN COARSE CATEGORY ----- #
print("\nAssigning coarse categories...")

# Maps top_web_name -> category label for the 6 comparison sites.
# TWITTER.COM and X (formerly Twitter) both map to TWITTER.COM.
COMPARISON_SITES = {
    'Netflix Inc.':             'Netflix Inc.',
    'Reddit':                   'Reddit',
    'Twitter':                  'Twitter',
    'X (formerly Twitter)':     'Twitter',
    'ONLYFANS.COM':             'ONLYFANS.COM',
    'New York Times Digital':   'New York Times Digital',
    'Facebook':                 'Facebook',
    'INSTRUCTURE.COM':          'INSTRUCTURE.COM',
    'Wikimedia Foundation Sites': 'Wikimedia Foundation Sites',
    'eBay':                     'eBay',
    'Amazon Sites':             'Amazon Sites',
    'DUCKDUCKGO.COM':           'DUCKDUCKGO.COM',
    'Enthusiast Gaming':        'Enthusiast Gaming',
    'Bytedance Inc.':           'Bytedance Inc.',
}

def assign_coarse_category(row):
    """Assign each session to a coarse category.
    Priority: XXX Adult > comparison sites / VPNclean > allVPN > all_other_sites
    """
    if row['subcategory'] == 'XXX Adult':
        if row['top_web_name'] in top_5_websites:
            return row['top_web_name']
        else:
            return 'other_XXX_sites'
    elif row['top_web_name'] in COMPARISON_SITES:
        return COMPARISON_SITES[row['top_web_name']]
    elif row['vpn_clean_site'] == True:
        return 'VPNclean'
    elif row['vpn_site'] == True:
        return 'allVPN'
    else:
        return 'all_other_sites'

sessions['coarse_category'] = sessions.apply(assign_coarse_category, axis=1)

# Verify categories
print("\nCoarse category distribution:")
category_counts = sessions['coarse_category'].value_counts()
all_categories = top_5_websites + ['other_XXX_sites'] + list(dict.fromkeys(COMPARISON_SITES.values())) + ['VPNclean', 'allVPN', 'all_other_sites']
for category in all_categories:
    count = category_counts.get(category, 0)
    print(f"  {category:40s}: {count:,}")

# ----- SELECT OUTPUT COLUMNS ----- #
print("\nPreparing output columns...")
output_columns = [
    'machine_id',
    'week_of_sample',
    'coarse_category',
    'duration',
]
sessions_output = sessions[output_columns].copy()

print(f"\nOutput shape: {sessions_output.shape}")
print(f"  Rows (sessions): {len(sessions_output):,}")
print(f"  Columns: {len(sessions_output.columns)}")

# ----- SAVE OUTPUT ----- #
print(f"\nSaving to {output_file}...")
sessions_output.to_parquet(output_file, index=False, engine='pyarrow')

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Processed month: {yyyymm}")
print(f"Sessions processed: {len(sessions_output):,}")
print(f"Weeks covered: {sessions_output['week_of_sample'].min()} to {sessions_output['week_of_sample'].max()}")
print(f"Coarse categories: {sessions_output['coarse_category'].nunique()}")
print(f"\nOutput saved to: {output_file}")
print("="*80)
print("COMPLETE")
print("="*80)
