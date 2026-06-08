# Author: Hannah Lybbert
# Created: 02/03/2026
# Purpose: Merge majority_state and minority_share onto desktop and mobile demographics

"""
Merges majority_state and minority_share from the DMA-ComScore-summary lookup
onto the raw desktop and mobile ComScore demographics files using the region field.

Run order:
    1. DMA_ComScore_Market.py          -> produces DMA_comscore_mapping.csv
    2. create_comscore_market_state.py -> produces comscore_market_state.csv
    3. merge_demos_to_state.py         -> this script

Input:
    - comscore_market_state.csv              (lookup: comscore_region -> majority_state, majority_share)
    - US_comscore_machine_demos_202201.txt       (desktop demographics, region in col 2)
    - US_comscore_mobile_demos_202201.txt        (mobile demographics, region in col 8)

Output:
    - desktop_demos_with_state_202201.csv
    - mobile_demos_with_state_202201.csv
"""

import pandas as pd
import os

# Set working directory - comment out for portability
# os.chdir(r"C:\Users\hlybbert\OneDrive - The University of Chicago\Documents\AgeVerification")

# Get the project root directory (3 levels up from this file)
file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(file_dir, "..", "..", ".."))

# File paths
lookup_file = os.path.join(project_root, "data", "ProcessAuxiliary", "DMA_market_state", "comscore_market_state.csv")

# Check for both .txt (local) and .txt.gz (cluster) versions of demographics files
desktop_file_base = os.path.join(project_root, "raw", "desktop_demographics", "US_comscore_machine_demos_202201.txt")
if os.path.exists(desktop_file_base):
    desktop_file = desktop_file_base
elif os.path.exists(desktop_file_base + ".gz"):
    desktop_file = desktop_file_base + ".gz"
else:
    raise FileNotFoundError(f"Could not find desktop demographics file at {desktop_file_base} or {desktop_file_base}.gz")

mobile_file_base = os.path.join(project_root, "raw", "mobile_demographics", "US_comscore_mobile_demos_202201.txt")
if os.path.exists(mobile_file_base):
    mobile_file = mobile_file_base
elif os.path.exists(mobile_file_base + ".gz"):
    mobile_file = mobile_file_base + ".gz"
else:
    raise FileNotFoundError(f"Could not find mobile demographics file at {mobile_file_base} or {mobile_file_base}.gz")

output_dir = os.path.join(project_root, "data", "ProcessAuxiliary", "DMA_market_state", "test")
os.makedirs(output_dir, exist_ok=True)
desktop_output = os.path.join(output_dir, "desktop_demos_with_state_202201.csv")
mobile_output = os.path.join(output_dir, "mobile_demos_with_state_202201.csv")

print("=" * 80)
print("Step 1: Loading lookup table")
print("=" * 80)

# Only need the market-to-state mapping columns
lookup = pd.read_csv(lookup_file, usecols=['comscore_region', 'majority_state', 'majority_share'])
print(f"Loaded {len(lookup)} markets in lookup")
print(f"Sample:\n{lookup.head()}")

print("\n" + "=" * 80)
print("Step 2: Desktop demographics")
print("=" * 80)

desktop_columns = ['machine_id', 'country', 'region', 'time_zone_bias', 'computer_location',
                   'hoh_age', 'hh_income', 'children_present', 'hh_size', 'month_id']

desktop_df = pd.read_csv(desktop_file, sep='\t', header=None, names=desktop_columns)
desktop_df['region'] = desktop_df['region'].str.replace('"', '', regex=False)
print(f"Loaded {len(desktop_df)} desktop records")
print(f"Unique regions: {desktop_df['region'].nunique()}")

# Merge on region == comscore_market_full
desktop_merged = desktop_df.merge(
    lookup,
    left_on='region',
    right_on='comscore_region',
    how='left'
).drop(columns='comscore_region')

matched = desktop_merged['majority_state'].notna().sum()
unmatched = desktop_merged['majority_state'].isna().sum()
print(f"\nDesktop merge results:")
print(f"  Matched: {matched} ({matched / len(desktop_merged) * 100:.1f}%)")
print(f"  Unmatched: {unmatched} ({unmatched / len(desktop_merged) * 100:.1f}%)")

if unmatched > 0:
    unmatched_regions = desktop_merged.loc[desktop_merged['majority_state'].isna(), 'region'].unique()
    print(f"  Unmatched regions: {sorted(unmatched_regions)}")

desktop_merged.to_csv(desktop_output, index=False)
print(f"\nSaved to {desktop_output}")

print("\n" + "=" * 80)
print("Step 3: Mobile demographics")
print("=" * 80)

mobile_columns = ['month_id', 'platform', 'machine_id', 'age', 'gender',
                  'hh_income', 'hh_size', 'children_present', 'region', 'race', 'hispanic']

mobile_df = pd.read_csv(mobile_file, sep='\t', header=None, names=mobile_columns)
mobile_df['region'] = mobile_df['region'].str.replace('"', '', regex=False)
print(f"Loaded {len(mobile_df)} mobile records")
print(f"Unique regions: {mobile_df['region'].nunique()}")

# Merge on region == comscore_market_full
mobile_merged = mobile_df.merge(
    lookup,
    left_on='region',
    right_on='comscore_region',
    how='left'
).drop(columns='comscore_region')

matched = mobile_merged['majority_state'].notna().sum()
unmatched = mobile_merged['majority_state'].isna().sum()
print(f"\nMobile merge results:")
print(f"  Matched: {matched} ({matched / len(mobile_merged) * 100:.1f}%)")
print(f"  Unmatched: {unmatched} ({unmatched / len(mobile_merged) * 100:.1f}%)")

if unmatched > 0:
    unmatched_regions = mobile_merged.loc[mobile_merged['majority_state'].isna(), 'region'].unique()
    print(f"  Unmatched regions: {sorted(unmatched_regions)}")

mobile_merged.to_csv(mobile_output, index=False)
print(f"\nSaved to {mobile_output}")
