# Author: Emily Davis
# Created: 02/05/2026
# Purpose: Create machine_id to state lookup for ComScore mobile data

'''
Input:
    - raw/mobile_demographics/US_comscore_mobile_demos_[YYYYMM].txt
    - data/ProcessAuxiliary/DMA_market_state/comscore_market_state.csv
Output:
    - data/ProcessComscore/intermediate/[month_id]/mobile_to_state_lookup.parquet
    - Columns: machine_id, state, majority_share

How to use in command line: python create_mobile_state_lookup.py YYYYMM
    Ex: python create_mobile_state_lookup.py 202201
'''

# Imports
import pandas as pd
import os
import sys

# ----- LOAD DATA ----- #
# Get YYYYMM from command line argument
if len(sys.argv) != 2:
    print("Usage: python create_mobile_state_lookup.py YYYYMM")
    print("Example: python create_mobile_state_lookup.py 202201")
    sys.exit(1)

yyyymm = sys.argv[1]

# ----- STEP 1: Get month_id from demographics file ----- #
demographics_path_base = f'raw/mobile_demographics/US_comscore_mobile_demos_{yyyymm}.txt'
if os.path.exists(demographics_path_base):
    demographics_path = demographics_path_base
    demo_compression = None
elif os.path.exists(demographics_path_base + '.gz'):
    demographics_path = demographics_path_base + '.gz'
    demo_compression = 'gzip'
else:
    print(f"ERROR: Mobile demographics file not found for {yyyymm}")
    print(f"  Tried: {demographics_path_base} and {demographics_path_base}.gz")
    sys.exit(1)

# Read just month_id to determine file paths
mobile_columns = ['month_id', 'platform', 'machine_id', 'age', 'gender',
                  'hh_income', 'hh_size', 'children_present', 'region', 'race', 'hispanic']

temp_demo = pd.read_csv(
    demographics_path,
    sep='\t',
    header=None,
    names=mobile_columns,
    usecols=['month_id'],
    nrows=1,
    compression=demo_compression
)
month_id = temp_demo['month_id'].iloc[0]

# ----- STEP 2: Load unique machine_ids from MOBILE SESSION file ----- #
print(f"\n[1/3] Loading unique machine_ids from mobile session file for month {month_id}...")
session_file_gz = f"raw/mobile_day_session/comscore_mobile_day_session_{month_id}m.txt.gz"
session_file_txt = f"raw/mobile_day_session/comscore_mobile_day_session_{month_id}m.txt"

if os.path.exists(session_file_gz):
    session_file = session_file_gz
    session_compression = 'gzip'
elif os.path.exists(session_file_txt):
    session_file = session_file_txt
    session_compression = None
else:
    print(f"ERROR: Mobile session file not found for month_id {month_id}")
    sys.exit(1)

# Load unique machine_ids from sessions
session_machines = pd.read_csv(
    session_file,
    sep='\t',
    header=None,
    names=['month_id', 'session_id', 'machine_id', 'platform', 'access_method_name',
           'time_id', 'calendar_day', 'event_time', 'ss2k', 'pages', 'duration', 'pattern_id'],
    usecols=['machine_id'],
    compression=session_compression,
    dtype={'machine_id': str}
)

# Get unique machine_ids
unique_machines = session_machines[['machine_id']].drop_duplicates()
print(f"  Found {len(unique_machines):,} unique mobile devices in session file")

# ----- STEP 3: Load demographics and merge ----- #
print(f"\n[2/3] Loading mobile demographics file...")
demographics = pd.read_csv(
    demographics_path,
    sep='\t',
    header=None,
    names=mobile_columns,
    usecols=['machine_id', 'region'],
    compression=demo_compression,
    dtype={'machine_id': str}
)

# Remove quotes from region names
demographics['region'] = demographics['region'].str.replace('"', '', regex=False)
print(f"  Loaded {len(demographics):,} mobile devices with demographics")

# Merge to get region for all session machines
unique_machines = unique_machines.merge(
    demographics[['machine_id', 'region']],
    on='machine_id',
    how='left'
)

machines_with_demo = unique_machines['region'].notna().sum()
machines_without_demo = unique_machines['region'].isna().sum()
print(f"\n  Devices with demographics: {machines_with_demo:,} ({(machines_with_demo/len(unique_machines))*100:.1f}%)")
print(f"  Devices without demographics: {machines_without_demo:,} ({(machines_without_demo/len(unique_machines))*100:.1f}%)")

# ----- STEP 4: Merge with market-to-state lookup ----- #
print(f"\n[3/3] Merging with market-to-state lookup...")
market_state_file = 'data/ProcessAuxiliary/DMA_market_state/comscore_market_state.csv'
market_state = pd.read_csv(market_state_file)

# Construct output path using month_id
output_dir = f"data/ProcessComscore/intermediate/{month_id}"
output_path = f"{output_dir}/mobile_to_state_lookup.parquet"

# Create output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

# Merge with market_state lookup to get state
lookup = unique_machines.merge(
    market_state[['comscore_region', 'majority_state', 'majority_share']],
    left_on='region',
    right_on='comscore_region',
    how='left'
)

# Rename columns
lookup = lookup.rename(columns={'majority_state': 'state'})
lookup = lookup[['machine_id', 'state', 'majority_share']]

# ----- STEP 5: Diagnose region-to-state matching ----- #
# Devices with demographics but no state match = region didn't match comscore_market_state.csv
has_region_no_state = (unique_machines['region'].notna() & lookup['state'].isna()).sum()
if has_region_no_state > 0:
    # Find which regions didn't match
    unmatched_regions = unique_machines.loc[
        unique_machines['region'].notna() & lookup['state'].isna(), 'region'
    ].value_counts()
    print(f"\n  WARNING: {has_region_no_state:,} devices have a region but no state match")
    print(f"  Top unmatched regions:")
    for region, count in unmatched_regions.head(10).items():
        print(f"    {region}: {count:,}")
else:
    print(f"\n  All devices with demographics matched to a state (or 'ZZ' for Unknown)")

# Region-to-state match rate (among devices with demographics)
if machines_with_demo > 0:
    region_state_matched = (lookup['state'].notna() & (unique_machines['region'].notna())).sum()
    print(f"  Region-to-state match rate: {region_state_matched:,} / {machines_with_demo:,} ({region_state_matched/machines_with_demo*100:.1f}%)")

# ----- STEP 6: Assign state codes for devices without data ----- #
print(f"\n[4/4] Assigning state codes...")

# Fill missing states with 'XX' (no demographics data available)
# Note: 'ZZ' is for devices with region='Unknown' (handled via lookup)
lookup['state'] = lookup['state'].fillna('XX')
lookup['majority_share'] = lookup['majority_share'].fillna(0.0)

# Ensure consistent types
lookup['machine_id'] = lookup['machine_id'].astype(str)

# ----- OUTPUT ----- #
print(f"\n[5/5] Saving output...")
lookup.to_parquet(output_path, index=False, engine='pyarrow')

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"Processing month: {yyyymm} (month_id: {month_id})")
print(f"Total mobile devices in sessions: {len(lookup):,}")
print(f"  With demographics & valid state: {((lookup['state'] != 'XX') & (lookup['state'] != 'ZZ')).sum():,} ({((lookup['state'] != 'XX') & (lookup['state'] != 'ZZ')).sum()/len(lookup)*100:.1f}%)")
print(f"  With unknown region (ZZ): {(lookup['state'] == 'ZZ').sum():,} ({(lookup['state'] == 'ZZ').sum()/len(lookup)*100:.1f}%)")
print(f"  Without demographics (XX): {(lookup['state'] == 'XX').sum():,} ({(lookup['state'] == 'XX').sum()/len(lookup)*100:.1f}%)")
print(f"\nOutput saved to: {output_path}")
print("=" * 60)
