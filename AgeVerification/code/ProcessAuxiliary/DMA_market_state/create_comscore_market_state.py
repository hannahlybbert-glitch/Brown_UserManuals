# Author: Hannah Lybbert
# Created: 02/03/2026
# Purpose: Merge DMA-ComScore mapping with DMA_summary to create ComScore Market -> State lookup

"""
Merges the clean DMA-to-ComScore market mapping (output of DMA_ComScore_Market.py)
with DMA_summary.csv to produce a single file mapping ComScore markets to DMAs
and their majority states.

Input:
    - DMA_comscore_mapping.csv  (DMA_code, DMA_name, DMA_majority_state, comscore_market_full)
    - DMA_summary.csv                 (DMA_code, DMA_name, majority_state, population, etc.)

Output:
    - comscore_market_state.csv   (comscore_region, majority_state, majority_share)
"""

import pandas as pd
import os

# Set working directory - comment out for portability
# os.chdir(r"C:\Users\hlybbert\OneDrive - The University of Chicago\Documents\AgeVerification")

# Get the project root directory (3 levels up from this file)
file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(file_dir, "..", "..", ".."))

# File paths
clean_mapping_file = os.path.join(project_root, "data", "ProcessAuxiliary", "DMA_market_state", "DMA_comscore_mapping.csv")
dma_summary_file = os.path.join(project_root, "data", "ProcessAuxiliary", "DMA_County", "DMA_summary.csv")
output_file = os.path.join(project_root, "data", "ProcessAuxiliary", "DMA_market_state", "comscore_market_state.csv")

print("=" * 80)
print("Step 1: Loading data")
print("=" * 80)

mapping_df = pd.read_csv(clean_mapping_file)
print(f"Loaded {len(mapping_df)} DMA-ComScore mappings")
print(f"Columns: {list(mapping_df.columns)}")

dma_summary = pd.read_csv(dma_summary_file)
print(f"\nLoaded {len(dma_summary)} DMAs from DMA_summary")
print(f"Columns: {list(dma_summary.columns)}")

print("\n" + "=" * 80)
print("Step 2: Merging")
print("=" * 80)

# Left join: keep all DMAs from DMA_summary, add comscore_market_full where available
merged = dma_summary.merge(
    mapping_df[['DMA_code', 'comscore_market_full']],
    on='DMA_code',
    how='left'
)

matched = merged['comscore_market_full'].notna().sum()
unmatched = merged['comscore_market_full'].isna().sum()
print(f"\nMerge results:")
print(f"  Total DMAs: {len(merged)}")
print(f"  Matched to ComScore market: {matched}")
print(f"  No ComScore match: {unmatched}")

if unmatched > 0:
    print(f"\nUnmatched DMAs:")
    print(merged.loc[merged['comscore_market_full'].isna(), ['DMA_code', 'DMA_name', 'majority_state']].to_string(index=False))

# Subset to final output columns, rename, and drop DMAs with no ComScore match
output = merged[['comscore_market_full', 'majority_state', 'majority_share']].rename(
    columns={'comscore_market_full': 'comscore_region'}
).dropna(subset=['comscore_region'])

print("\nSample output:")
print(output.head(10).to_string(index=False))

print("\n" + "=" * 80)
print("Step 3: Adding special cases")
print("=" * 80)

# Add 'Unknown' region with state = 'ZZ'
# This handles machines that have region = 'Unknown' in demographics
unknown_row = pd.DataFrame({
    'comscore_region': ['Unknown'],
    'majority_state': ['ZZ'],
    'majority_share': [1.0]
})

output = pd.concat([output, unknown_row], ignore_index=True)
print("\nAdded special case: 'Unknown' region -> state 'ZZ'")

print("\n" + "=" * 80)
print("Step 4: Saving")
print("=" * 80)

output.to_csv(output_file, index=False)
print(f"\nSaved to {output_file}")
print(f"Total markets: {len(output)}")
print(f"Note: This includes {len(output) - 1} ComScore markets plus 1 'Unknown' region")
print(f"Output columns: {list(output.columns)}")
