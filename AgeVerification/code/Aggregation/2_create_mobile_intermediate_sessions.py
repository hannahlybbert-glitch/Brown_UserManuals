# Author: Emily Davis
# Created: 03/10/2026
# Purpose: Create intermediate session-level files for mobile data with week_of_sample and coarse_category

"""
Create Mobile Intermediate Session Files (Per Month)
Processes one month at a time, adding week_of_sample and coarse_category to mobile session data.
Outputs SESSION-LEVEL data (not aggregated) for final aggregation script.

Mirrors 2_create_intermediate_sessions.py for the desktop pipeline.

Usage: python 2_create_mobile_intermediate_sessions.py YYYYMM
Example: python 2_create_mobile_intermediate_sessions.py 202201

Input:
- merged_mobile_sessions_YYYYMM.parquet
- top5_xxx_websites.csv (from desktop script 1 — shared across both pipelines)
- comscore_time_lookup_YYYYMM.txt

Output:
- mobile_intermediate_sessions_YYYYMM.parquet (session-level with week and coarse category)

Coarse Categories (9 total):
- Top 5 XXX Adult websites (by name) — same sites as desktop, tracked consistently
- other_XXX_sites — All other XXX Adult websites not in top 5 (pooled)
- VPNclean — Top 3 pure VPN providers (NordVPN, ExpressVPN, Surfshark)
- allVPN — All other whitelisted VPN sites
- all_other_sites — All non-XXX, non-VPN websites

Note on VPN flags:
  vpn_site and vpn_clean_site are read directly from merged_mobile_sessions, where
  they are set by create_web_characteristics.py in the ProcessComscore pipeline.

Note on background app sessions:
  Sessions with pages=0 are excluded. These are background app data calls with no
  content rendered. Browser sessions never have pages=0, so this filter only affects
  app sessions. The remaining right tail is handled by p95 winsorization in analysis.
"""

import pandas as pd
import os
import sys

project_root = os.getcwd()

# ----- COMMAND LINE ARGUMENTS ----- #
if len(sys.argv) != 2:
    print("Usage: python 2_create_mobile_intermediate_sessions.py YYYYMM")
    print("Example: python 2_create_mobile_intermediate_sessions.py 202201")
    sys.exit(1)

yyyymm = sys.argv[1]

print("="*80)
print(f"CREATING MOBILE INTERMEDIATE SESSIONS FOR {yyyymm}")
print("="*80)

# ----- FILE PATHS ----- #
sessions_file = os.path.join(project_root, "data", "ProcessComscore", "merged_session_files",
                             f"merged_mobile_sessions_{yyyymm}.parquet")
top_websites_file = os.path.join(project_root, "data", "Aggregation", "top5_xxx_websites.csv")

# Check for both .txt (local) and .txt.gz (cluster) versions
time_lookup_base = os.path.join(project_root, "raw", "Lookups", "time_lookup",
                                f"comscore_time_lookup_{yyyymm}.txt")
if os.path.exists(time_lookup_base):
    time_lookup_file = time_lookup_base
elif os.path.exists(time_lookup_base + ".gz"):
    time_lookup_file = time_lookup_base + ".gz"
else:
    raise FileNotFoundError(
        f"Could not find time lookup file at {time_lookup_base} or {time_lookup_base}.gz"
    )

# ----- LOAD DATA ----- #
print(f"\n[1/5] Loading mobile sessions for {yyyymm}...")
columns_to_read = ['machine_id', 'time_id', 'duration', 'top_web_name', 'subcategory', 'month_id',
                   'pages', 'vpn_site', 'vpn_clean_site']
sessions = pd.read_parquet(sessions_file, columns=columns_to_read)
print(f"  Loaded {len(sessions):,} sessions")

month_id = sessions['month_id'].iloc[0]
print(f"  Month ID: {month_id}")

# Set up output paths
output_dir = os.path.join(project_root, "data", "Aggregation", "mobile_intermediate", str(month_id))
output_file = os.path.join(output_dir, f"mobile_intermediate_sessions_{yyyymm}.parquet")
os.makedirs(output_dir, exist_ok=True)

print(f"\n[2/5] Loading top 5 XXX Adult websites (shared with desktop pipeline)...")
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

sessions_before_filter = len(sessions)
sessions = sessions[sessions['duration'] > 0].copy()
print(f"  After filtering zero duration: {len(sessions):,} sessions "
      f"({(len(sessions)/sessions_before_filter)*100:.1f}% retained)")

# Winsorize duration at 95th percentile
p95_duration = sessions['duration'].quantile(0.95)
sessions['duration'] = sessions['duration'].clip(upper=p95_duration)
print(f"  Winsorized duration at 95th percentile: {p95_duration:.1f}")

# Exclude background app sessions (pages=0 means no content rendered — background data call).
# Browser sessions never have pages=0, so this filter only affects app sessions.
sessions_before_pages_filter = len(sessions)
sessions = sessions[sessions['pages'] > 0].copy()
print(f"  After filtering pages=0:       {len(sessions):,} sessions "
      f"({(len(sessions)/sessions_before_pages_filter)*100:.1f}% retained)")

# ----- CREATE WEEK_OF_SAMPLE VARIABLE ----- #
print("\n[5/5] Creating week_of_sample variable...")

base_date = pd.to_datetime('2022-01-01')
sessions['date_parsed'] = pd.to_datetime(sessions['date'])
sessions['days_since_base'] = (sessions['date_parsed'] - base_date).dt.days
sessions['week_of_sample'] = sessions['days_since_base'] // 7 + 1

print(f"  Base date: {base_date.strftime('%Y-%m-%d')}")
print(f"  Week range in {yyyymm}: {sessions['week_of_sample'].min()} to {sessions['week_of_sample'].max()}")
print(f"  Date range: {sessions['date_parsed'].min().date()} to {sessions['date_parsed'].max().date()}")
print(f"  Unique weeks: {sessions['week_of_sample'].nunique()}")

# ----- VPN FLAGS ----- #
print("\nVPN flags (from merged_mobile_sessions):")
print(f"  vpn_clean_site=True: {sessions['vpn_clean_site'].sum():,} sessions")
print(f"  vpn_site=True:       {sessions['vpn_site'].sum():,} sessions")

# ----- ASSIGN COARSE CATEGORY ----- #
# Vectorized assignment in priority order (lowest to highest).
# Later assignments override earlier ones, so XXX Adult takes final precedence.
# Priority: XXX Adult > comparison sites / VPNclean > allVPN > all_other_sites
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

top_5_set = set(top_5_websites)
sessions['coarse_category'] = 'all_other_sites'
sessions.loc[sessions['vpn_site'],           'coarse_category'] = 'allVPN'
sessions.loc[sessions['vpn_clean_site'],     'coarse_category'] = 'VPNclean'
sessions.loc[sessions['top_web_name'].isin(COMPARISON_SITES), 'coarse_category'] = \
    sessions['top_web_name'].map(COMPARISON_SITES)
is_xxx = sessions['subcategory'] == 'XXX Adult'
sessions.loc[is_xxx,                         'coarse_category'] = 'other_XXX_sites'
is_top5 = is_xxx & sessions['top_web_name'].isin(top_5_set)
sessions.loc[is_top5,                        'coarse_category'] = sessions.loc[is_top5, 'top_web_name']

print("\nCoarse category distribution:")
category_counts = sessions['coarse_category'].value_counts()
all_categories = top_5_websites + ['other_XXX_sites'] + list(dict.fromkeys(COMPARISON_SITES.values())) + ['VPNclean', 'allVPN', 'all_other_sites']
for category in all_categories:
    count = category_counts.get(category, 0)
    print(f"  {category:40s}: {count:,}")

# ----- SELECT OUTPUT COLUMNS ----- #
output_columns = ['machine_id', 'week_of_sample', 'coarse_category', 'duration']
sessions_output = sessions[output_columns].copy()

print(f"\nOutput shape: {sessions_output.shape}")

# ----- SAVE OUTPUT ----- #
print(f"\nSaving to {output_file}...")
sessions_output.to_parquet(output_file, index=False, engine='pyarrow')

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Processed month: {yyyymm} (month_id: {month_id})")
print(f"Sessions processed: {len(sessions_output):,}")
print(f"Weeks covered: {sessions_output['week_of_sample'].min()} to {sessions_output['week_of_sample'].max()}")
print(f"Coarse categories: {sessions_output['coarse_category'].nunique()}")
print(f"\nOutput saved to: {output_file}")
print("="*80)
print("COMPLETE")
print("="*80)
