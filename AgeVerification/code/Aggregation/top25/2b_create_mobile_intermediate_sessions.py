# Author: Hannah Lybbert, assisted by Claude
# Created: 2026-05-21
# Purpose: Create top-25 mobile intermediate session files — XXX Adult sessions only,
#          categorised as one of the top 25 sites or other_adult.
#
# Mirrors 2b_create_intermediate_sessions.py for the mobile pipeline.
# Adds the pages > 0 filter (background app sessions have pages=0).
#
# Usage: python3 code/Aggregation/top25/2b_create_mobile_intermediate_sessions.py YYYYMM
#
# Input:
#   data/ProcessComscore/merged_session_files/merged_mobile_sessions_{YYYYMM}.parquet
#   output/ProcessComscore/data_structure_validation/top25_adult_sites.csv
#   raw/Lookups/time_lookup/comscore_time_lookup_{YYYYMM}.txt[.gz]
#
# Output:
#   data/Aggregation/top25/mobile_intermediate/{month_id}/mobile_intermediate_sessions_{YYYYMM}.parquet
#   Columns: machine_id, week_of_sample, coarse_category, duration

import pandas as pd
import os
import sys

project_root = os.getcwd()

if len(sys.argv) != 2:
    print("Usage: python3 code/Aggregation/top25/2b_create_mobile_intermediate_sessions.py YYYYMM")
    sys.exit(1)

yyyymm = sys.argv[1]

print("=" * 80)
print(f"TOP-25 INTERMEDIATE SESSIONS (MOBILE): {yyyymm}")
print("=" * 80)

# ----- FILE PATHS ----- #
sessions_file = os.path.join(
    project_root, "data", "ProcessComscore", "merged_session_files",
    f"merged_mobile_sessions_{yyyymm}.parquet"
)
top25_file = os.path.join(
    project_root, "output", "ProcessComscore", "data_structure_validation",
    "top25_adult_sites.csv"
)
time_lookup_base = os.path.join(
    project_root, "raw", "Lookups", "time_lookup",
    f"comscore_time_lookup_{yyyymm}.txt"
)
if os.path.exists(time_lookup_base):
    time_lookup_file = time_lookup_base
elif os.path.exists(time_lookup_base + ".gz"):
    time_lookup_file = time_lookup_base + ".gz"
else:
    raise FileNotFoundError(
        f"Time lookup not found at {time_lookup_base} or {time_lookup_base}.gz"
    )

# ----- LOAD DATA ----- #
print(f"\n[1/5] Loading mobile sessions for {yyyymm}...")
columns_to_read = [
    'machine_id', 'time_id', 'duration', 'top_web_name',
    'subcategory', 'month_id', 'pages'
]
sessions = pd.read_parquet(sessions_file, columns=columns_to_read)
print(f"  Loaded {len(sessions):,} sessions")

month_id = sessions['month_id'].iloc[0]
print(f"  Month ID: {month_id}")

output_dir = os.path.join(
    project_root, "data", "Aggregation", "top25", "mobile_intermediate", str(month_id)
)
output_file = os.path.join(output_dir, f"mobile_intermediate_sessions_{yyyymm}.parquet")
os.makedirs(output_dir, exist_ok=True)

print(f"\n[2/5] Loading top 25 adult sites...")
top25 = pd.read_csv(top25_file)
top_25_sites = top25['top_web_name'].tolist()
print(f"  Sites loaded: {len(top_25_sites)}")

print(f"\n[3/5] Loading time lookup for {yyyymm}...")
time_lookup = pd.read_csv(
    time_lookup_file, sep='\t', header=None,
    names=['time_id', 'week_id', 'unknown', 'date']
)
print(f"  Loaded {len(time_lookup):,} days")

# ----- MERGE TIME INFORMATION AND FILTER ----- #
print("\n[4/5] Merging with time lookup and applying filters...")
sessions = sessions.merge(time_lookup[['time_id', 'date']], on='time_id', how='left')

n_before = len(sessions)
sessions = sessions[sessions['duration'] > 0].copy()
print(f"  After filtering zero duration: {len(sessions):,} ({len(sessions)/n_before*100:.1f}% retained)")

# Winsorize at p95 of all sessions (consistent with original pipeline)
p95_duration = sessions['duration'].quantile(0.95)
sessions['duration'] = sessions['duration'].clip(upper=p95_duration)
print(f"  Winsorized at p95: {p95_duration:.1f}s")

# Mobile-specific: drop background app sessions (pages=0 means no content rendered)
n_before_pages = len(sessions)
sessions = sessions[sessions['pages'] > 0].copy()
print(f"  After filtering pages=0: {len(sessions):,} ({len(sessions)/n_before_pages*100:.1f}% retained)")

base_date = pd.to_datetime('2022-01-01')
sessions['date_parsed'] = pd.to_datetime(sessions['date'])
sessions['days_since_base'] = (sessions['date_parsed'] - base_date).dt.days
sessions['week_of_sample'] = sessions['days_since_base'] // 7 + 1
print(f"  Week range: {sessions['week_of_sample'].min()} to {sessions['week_of_sample'].max()}")

# ----- FILTER TO XXX ADULT AND ASSIGN CATEGORY ----- #
print("\n[5/5] Filtering to XXX Adult and assigning coarse categories...")

sessions_xxx = sessions[sessions['subcategory'] == 'XXX Adult'].copy()
print(f"  XXX Adult sessions: {len(sessions_xxx):,} of {len(sessions):,} total")

# Vectorized assignment: top 25 sites by name, everything else → other_adult
top_25_set = set(top_25_sites)
sessions_xxx['coarse_category'] = 'other_adult'
is_top25 = sessions_xxx['top_web_name'].isin(top_25_set)
sessions_xxx.loc[is_top25, 'coarse_category'] = sessions_xxx.loc[is_top25, 'top_web_name']

print(f"\n  Category distribution:")
cat_counts = sessions_xxx['coarse_category'].value_counts()
for site in top_25_sites:
    print(f"    {site:35s}: {cat_counts.get(site, 0):>10,}")
print(f"    {'other_adult':35s}: {cat_counts.get('other_adult', 0):>10,}")

# ----- SAVE OUTPUT ----- #
output_cols = ['machine_id', 'week_of_sample', 'coarse_category', 'duration']
sessions_output = sessions_xxx[output_cols].copy()

print(f"\nOutput shape: {sessions_output.shape}")
print(f"Saving to {output_file}...")
sessions_output.to_parquet(output_file, index=False, engine='pyarrow')

print("\n" + "=" * 80)
print(f"COMPLETE — {yyyymm}")
print(f"  Sessions output: {len(sessions_output):,}")
print(f"  Output: {output_file}")
print("=" * 80)
