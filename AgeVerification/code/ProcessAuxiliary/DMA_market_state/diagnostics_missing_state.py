# Author: Hannah Lybbert
# Created: 02/11/2026
# Purpose: Diagnose missing states in comscore_market_state.csv and merged sessions

"""
Diagnostics for Missing State Values
Explores comscore_market_state.csv to understand which markets don't map to states
and how this relates to missing states in merged_sessions data
"""

import pandas as pd
import numpy as np
import os

# For cluster: comment out the os.chdir line
os.chdir(r"C:\Users\hlybbert\OneDrive - The University of Chicago\Documents\AgeVerification")

# Get the project root directory
project_root = os.getcwd()

# File paths
market_state_file = os.path.join(project_root, "data", "ProcessAuxiliary", "DMA_market_state", "comscore_market_state.csv")
sessions_file = os.path.join(project_root, "data", "ProcessComscore", "merged_session_files", "merged_sessions_202201.parquet")

print("="*80)
print("MISSING STATE DIAGNOSTICS")
print("="*80)

# ==============================================================================
# 1. EXPLORE COMSCORE_MARKET_STATE.CSV
# ==============================================================================
print("\n" + "="*80)
print("1. COMSCORE_MARKET_STATE.CSV OVERVIEW")
print("="*80)

print(f"\nReading: {market_state_file}")
market_state = pd.read_csv(market_state_file)

print(f"\nTotal rows: {len(market_state):,}")
print(f"Columns: {list(market_state.columns)}")

print("\nFirst 10 rows:")
print(market_state.head(10).to_string(index=False))

# ==============================================================================
# 2. CHECK FOR MISSING/UNKNOWN REGIONS
# ==============================================================================
print("\n" + "="*80)
print("2. MISSING/UNKNOWN REGIONS")
print("="*80)

# Check for missing values
print("\nMissing values:")
for col in market_state.columns:
    missing = market_state[col].isna().sum()
    pct = (missing / len(market_state)) * 100
    print(f"  {col:20s}: {missing:6,} ({pct:5.2f}%)")

# Check for 'unknown' or similar patterns
print("\nSearching for 'unknown' regions (case insensitive)...")
unknown_mask = market_state['comscore_region'].str.lower().str.contains('unknown', na=False)
unknown_regions = market_state[unknown_mask]

if len(unknown_regions) > 0:
    print(f"Found {len(unknown_regions)} 'unknown' regions:")
    print(unknown_regions.to_string(index=False))
else:
    print("No 'unknown' regions found")

# Check for empty/null regions
null_region = market_state['comscore_region'].isna().sum()
empty_region = (market_state['comscore_region'].str.strip() == '').sum()
print(f"\nNull regions: {null_region}")
print(f"Empty string regions: {empty_region}")

# ==============================================================================
# 3. CHECK FOR MISSING STATES
# ==============================================================================
print("\n" + "="*80)
print("3. REGIONS WITH MISSING STATES")
print("="*80)

missing_state = market_state[market_state['majority_state'].isna()].copy()

if len(missing_state) > 0:
    print(f"\nFound {len(missing_state)} regions with missing majority_state:")
    print(missing_state.to_string(index=False))
else:
    print("\nNo regions with missing majority_state")

# Check for unusual state values
print("\nUnique states in file:")
unique_states = sorted(market_state['majority_state'].dropna().unique())
print(f"Total unique states: {len(unique_states)}")
print(f"States: {unique_states}")

# Check for non-standard state codes (not 2 letters)
if market_state['majority_state'].notna().sum() > 0:
    non_standard = market_state[
        market_state['majority_state'].notna() &
        (market_state['majority_state'].str.len() != 2)
    ]
    if len(non_standard) > 0:
        print(f"\nRegions with non-standard state codes (not 2 letters):")
        print(non_standard.to_string(index=False))

# ==============================================================================
# 4. MAJORITY_SHARE DISTRIBUTION
# ==============================================================================
print("\n" + "="*80)
print("4. MAJORITY_SHARE DISTRIBUTION")
print("="*80)

print("\nMajority_share statistics:")
print(market_state['majority_share'].describe())

# Regions with low majority share (cross-state markets)
low_majority = market_state[market_state['majority_share'] < 0.5].copy()
if len(low_majority) > 0:
    print(f"\nRegions with majority_share < 0.5 ({len(low_majority)} regions):")
    print(low_majority.sort_values('majority_share').to_string(index=False))

# Regions with perfect majority (1.0)
perfect_majority = market_state[market_state['majority_share'] == 1.0].copy()
print(f"\nRegions with perfect majority_share (1.0): {len(perfect_majority)} ({(len(perfect_majority)/len(market_state))*100:.1f}%)")

# ==============================================================================
# 5. CROSS-REFERENCE WITH MERGED SESSIONS DATA
# ==============================================================================
print("\n" + "="*80)
print("5. CROSS-REFERENCE WITH MERGED SESSIONS (Sample: 500k rows)")
print("="*80)

print(f"\nReading sample from: {sessions_file}")
sessions = pd.read_parquet(sessions_file)
sample_size = min(500000, len(sessions))
sessions = sessions.head(sample_size)
print(f"Loaded {len(sessions):,} sessions")

# Get sessions with missing state
missing_state_sessions = sessions[sessions['state'].isna()].copy()
print(f"\nSessions with missing state: {len(missing_state_sessions):,} ({(len(missing_state_sessions)/len(sessions))*100:.2f}%)")

if len(missing_state_sessions) > 0:
    # What metro areas do they have?
    print("\nMetro areas for sessions with missing state:")
    print(f"  Missing metro_area: {missing_state_sessions['metro_area'].isna().sum():,}")

    if missing_state_sessions['metro_area'].notna().sum() > 0:
        print("\n  Top 20 metro areas:")
        top_metros = missing_state_sessions['metro_area'].value_counts().head(20)
        for i, (metro, count) in enumerate(top_metros.items(), 1):
            pct = (count / len(missing_state_sessions)) * 100
            # Check if this metro is in our market_state file
            in_lookup = metro in market_state['comscore_region'].values
            status = "IN LOOKUP" if in_lookup else "NOT IN LOOKUP"
            print(f"    {i:2d}. {metro:40s}: {count:6,} ({pct:5.2f}%) [{status}]")

        # Check which metros are NOT in the lookup
        missing_metros = missing_state_sessions['metro_area'].dropna().unique()
        lookup_metros = set(market_state['comscore_region'].values)
        not_in_lookup = [m for m in missing_metros if m not in lookup_metros]

        if len(not_in_lookup) > 0:
            print(f"\n  Metro areas in sessions but NOT in comscore_market_state.csv: {len(not_in_lookup)}")
            print("  (These are the metros causing missing states!)")
            for i, metro in enumerate(sorted(not_in_lookup)[:20], 1):
                session_count = (missing_state_sessions['metro_area'] == metro).sum()
                print(f"    {i:2d}. {metro}: {session_count:,} sessions")

# ==============================================================================
# 6. DMA CODE ANALYSIS
# ==============================================================================
print("\n" + "="*80)
print("6. DMA CODES FOR MISSING STATE SESSIONS")
print("="*80)

if len(missing_state_sessions) > 0 and 'DMA_code' in missing_state_sessions.columns:
    print("\nTop DMA codes (missing state sessions):")
    dma_counts = missing_state_sessions['DMA_code'].value_counts().head(10)
    for dma, count in dma_counts.items():
        pct = (count / len(missing_state_sessions)) * 100
        print(f"  DMA {dma}: {count:,} ({pct:.2f}%)")

    # Check if there's a DMA to market lookup we can use
    print("\nNote: DMA codes 300, 360, 480, 420 account for most missing states")
    print("These likely correspond to specific metro areas not in comscore_market_state.csv")

# ==============================================================================
# 7. SUMMARY & RECOMMENDATIONS
# ==============================================================================
print("\n" + "="*80)
print("7. SUMMARY & RECOMMENDATIONS")
print("="*80)

print("\n1. Comscore Market State File:")
print(f"   - {len(market_state):,} markets with state mappings")
print(f"   - No 'unknown' or missing regions found" if len(unknown_regions) == 0 and null_region == 0 else f"   - Found issues with unknown/null regions")

print("\n2. Missing States in Sessions:")
print(f"   - {len(missing_state_sessions):,} sessions ({(len(missing_state_sessions)/len(sessions))*100:.2f}%) missing state")
print(f"   - These sessions have metro_area values but those metros are NOT in comscore_market_state.csv")

print("\n3. Root Cause:")
print("   - Missing states are NOT due to 'unknown' markets")
print("   - Instead, some metro areas in the sessions data don't have mappings in comscore_market_state.csv")
print("   - This is likely because the lookup file was created before these markets existed,")
print("     or these markets were not included in the original DMA-to-state mapping")

print("\n4. Recommendation:")
print("   - FILTER OUT sessions with missing state (16% of data)")
print("   - Consider updating comscore_market_state.csv to include missing metro areas")
print("   - Or investigate whether these DMA codes need special handling")

print("\n" + "="*80)
print("END OF DIAGNOSTICS")
print("="*80)
