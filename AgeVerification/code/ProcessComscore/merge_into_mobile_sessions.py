# Author: Emily Davis
# Created: 02/18/2026
# Purpose: Merge mobile session file with crosswalk, web characteristics, and mobile demographics

'''
Input:
    - raw/mobile_day_session/comscore_mobile_day_session_{month_id}m.txt[.gz]
    - data/ProcessComscore/intermediate/{month_id}/crosswalk.parquet
    - data/ProcessComscore/intermediate/{month_id}/web_characteristics.parquet
    - data/ProcessComscore/mobile_characteristics.csv
    - data/ProcessComscore/intermediate/{month_id}/mobile_to_state_lookup.parquet
Output:
    - data/ProcessComscore/merged_session_files/merged_mobile_sessions_{YYYYMM}.parquet

How to use in command line: python merge_into_mobile_sessions.py YYYYMM
    Ex: python merge_into_mobile_sessions.py 202201
'''

# Imports
import pandas as pd
import numpy as np
import os
import sys


# ----- LOAD DATA ----- #
# Get YYYYMM from command line argument
if len(sys.argv) != 2:
    print("Usage: python merge_into_mobile_sessions.py YYYYMM")
    print("Example: python merge_into_mobile_sessions.py 202201")
    sys.exit(1)

yyyymm = sys.argv[1]

# Get month_id by reading the category map file (try .gz first, then .txt)
cat_map_gz = f'raw/Lookups/traffic_category_map/comscore_category_map_{yyyymm}.txt.gz'
cat_map_txt = f'raw/Lookups/traffic_category_map/comscore_category_map_{yyyymm}.txt'

if os.path.exists(cat_map_gz):
    cat_map_path = cat_map_gz
    cat_compression = 'gzip'
elif os.path.exists(cat_map_txt):
    cat_map_path = cat_map_txt
    cat_compression = None
else:
    print(f"ERROR: Category map file not found for {yyyymm}")
    sys.exit(1)

temp_category_map = pd.read_csv(cat_map_path, sep='\t', header=None, nrows=1, compression=cat_compression)
month_id = temp_category_map.iloc[0, 0]

# Construct file paths
intermediate_dir = f"data/ProcessComscore/intermediate/{month_id}"
output_dir = "data/ProcessComscore/merged_session_files"

# Try both compressed and uncompressed session files
session_file_gz = f"raw/mobile_day_session/comscore_mobile_day_session_{month_id}m.txt.gz"
session_file_txt = f"raw/mobile_day_session/comscore_mobile_day_session_{month_id}m.txt"

if os.path.exists(session_file_gz):
    session_file = session_file_gz
    compression = 'gzip'
elif os.path.exists(session_file_txt):
    session_file = session_file_txt
    compression = None
else:
    print(f"ERROR: Mobile session file not found for month_id {month_id}")
    print(f"  Tried: {session_file_gz}")
    print(f"  Tried: {session_file_txt}")
    sys.exit(1)

crosswalk_file = f"{intermediate_dir}/crosswalk.parquet"
web_char_file = f"{intermediate_dir}/web_characteristics.parquet"
mobile_char_file = "data/ProcessComscore/mobile_characteristics.csv"
mobile_state_file = f"{intermediate_dir}/mobile_to_state_lookup.parquet"
output_file = f"{output_dir}/merged_mobile_sessions_{yyyymm}.parquet"

# Create output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

print("=" * 60)
print(f"MOBILE MERGE PIPELINE: {yyyymm} (month_id: {month_id})")
print("=" * 60)

# Load mobile session file
print(f"\n[1/5] Loading mobile session file: {session_file}")
day_session = pd.read_csv(
    session_file, sep='\t', header=None,
    names=['month_id', 'session_id', 'machine_id', 'platform', 'access_method_name',
           'time_id', 'calendar_day', 'event_time', 'ss2k', 'pages', 'duration', 'pattern_id'],
    dtype={'machine_id': str, 'pattern_id': str},
    compression=compression,
    low_memory=False
)
print(f"  Loaded {len(day_session):,} sessions")
print(f"  Unique machines: {day_session['machine_id'].nunique():,}")

# Load crosswalk
print(f"\n[2/5] Loading crosswalk: {crosswalk_file}")
crosswalk = pd.read_parquet(crosswalk_file)
crosswalk['pattern_id'] = crosswalk['pattern_id'].astype(str)
print(f"  Loaded {len(crosswalk):,} pattern_id mappings")

# Load web characteristics
print(f"\n[3/5] Loading web characteristics: {web_char_file}")
website_info = pd.read_parquet(web_char_file)
website_info['top_web_id'] = website_info['top_web_id'].astype(str)
print(f"  Loaded {len(website_info):,} website records")

# Load mobile characteristics
print(f"\n[4/5] Loading mobile characteristics: {mobile_char_file}")
mobile_chars = pd.read_csv(mobile_char_file, dtype={'machine_id': str})
print(f"  Loaded {len(mobile_chars):,} machine records")

# Load mobile state lookup
print(f"\n[5/5] Loading mobile state lookup: {mobile_state_file}")
mobile_state = pd.read_parquet(mobile_state_file)
mobile_state['machine_id'] = mobile_state['machine_id'].astype(str)
print(f"  Loaded {len(mobile_state):,} machine state records")


# ----- FILTER TO STATIC PANEL ----- #
print("\n" + "-" * 60)
print("FILTERING TO STATIC PANEL (machines with demographics)")
print("-" * 60)

static_machines = set(mobile_chars['machine_id'].unique())
initial_sessions = len(day_session)
initial_machines = day_session['machine_id'].nunique()

day_session = day_session[day_session['machine_id'].isin(static_machines)]

filtered_sessions = len(day_session)
filtered_machines = day_session['machine_id'].nunique()
sessions_dropped = initial_sessions - filtered_sessions
machines_dropped = initial_machines - filtered_machines

print(f"  Initial: {initial_sessions:,} sessions from {initial_machines:,} machines")
print(f"  Machines not in Static panel: {machines_dropped:,} ({machines_dropped/initial_machines*100:.1f}%)")
print(f"  Sessions dropped: {sessions_dropped:,} ({sessions_dropped/initial_sessions*100:.1f}%)")
print(f"  Remaining: {filtered_sessions:,} sessions from {filtered_machines:,} machines")


# ----- MERGE DATA ----- #
print("\n" + "-" * 60)
print("MERGING DATA")
print("-" * 60)

# Step 1: Merge crosswalk onto session file (on pattern_id)
print("\n  Step 1: Merging crosswalk (pattern_id -> top_web_id)...")
df_merge1 = day_session.merge(crosswalk, on='pattern_id', how='left')
crosswalk_match = df_merge1['top_web_id'].notna().sum()
crosswalk_rate = crosswalk_match / len(df_merge1) * 100 if len(df_merge1) > 0 else 0
print(f"    Matched: {crosswalk_match:,} / {len(df_merge1):,} ({crosswalk_rate:.1f}%)")

# Step 2: Merge web characteristics (on top_web_id)
print("\n  Step 2: Merging web characteristics...")
df_merge2 = df_merge1.merge(website_info, on='top_web_id', how='left')
web_match = df_merge2['top_web_name'].notna().sum()
web_rate = web_match / len(df_merge2) * 100 if len(df_merge2) > 0 else 0
print(f"    Matched: {web_match:,} / {len(df_merge2):,} ({web_rate:.1f}%)")

# Step 3: Merge mobile characteristics (on machine_id)
# Note: both session and demographics have 'platform'; use suffixes to distinguish
print("\n  Step 3: Merging mobile characteristics...")
df_merge3 = df_merge2.merge(mobile_chars, on='machine_id', how='left', suffixes=('', '_demo'))
mobile_match = df_merge3['age'].notna().sum()
mobile_rate = mobile_match / len(df_merge3) * 100 if len(df_merge3) > 0 else 0
print(f"    Matched: {mobile_match:,} / {len(df_merge3):,} ({mobile_rate:.1f}%)")

# Step 4: Merge mobile state lookup (on machine_id)
print("\n  Step 4: Merging mobile state lookup...")
df_merged = df_merge3.merge(mobile_state, on='machine_id', how='left')
state_match = df_merged['state'].notna().sum()
state_rate = state_match / len(df_merged) * 100 if len(df_merged) > 0 else 0
print(f"    Matched: {state_match:,} / {len(df_merged):,} ({state_rate:.1f}%)")


# ----- SAVE OUTPUT ----- #
print("\n" + "-" * 60)
print("SAVING OUTPUT")
print("-" * 60)

df_merged.to_parquet(output_file, index=False)
file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
print(f"  Output file: {output_file}")
print(f"  File size: {file_size_mb:.1f} MB")


# ----- SUMMARY ----- #
print("\n" + "=" * 60)
print("MERGE COMPLETE - SUMMARY")
print("=" * 60)
print(f"  Month: {yyyymm} (month_id: {month_id})")
print(f"  Total sessions: {len(df_merged):,}")
print(f"  Unique machines: {df_merged['machine_id'].nunique():,}")
print(f"  Total columns: {len(df_merged.columns)}")
print(f"\n  Columns: {list(df_merged.columns)}")

# Top 10 categories
print("\n  Top 10 categories by session count:")
category_counts = df_merged['category'].value_counts().head(10)
for cat, count in category_counts.items():
    pct = count / len(df_merged) * 100
    print(f"    {cat}: {count:,} ({pct:.2f}%)")

print("=" * 60)
