# Author: Hannah Lybbert
# Created: 01/28/2026
# Updated: 01/29/2026
# Purpose: Investigate unmatched counties between ZIP to DMA and county population files

import pandas as pd
import os

# Change working directory - comment out for portability
# os.chdir(r"C:\Users\hlybbert\OneDrive - The University of Chicago\Documents\AgeVerification")

# Get the project root directory (3 levels up from this file)
file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(file_dir, "..", "..", ".."))

# Read both files
zip_dma = pd.read_csv(os.path.join(project_root, "data", "ProcessAuxiliary", "DMA_County", "ZIP_to_DMA_clean.csv"))
county_pop = pd.read_csv(os.path.join(project_root, "data", "ProcessAuxiliary", "DMA_County", "co_est2022_pop_standardized.csv"))

# Get unique county-state combinations (filter out NaN values)
dma_counties = zip_dma[['county', 'state']].dropna().drop_duplicates()

# Merge to find unmatched
dma_counties_with_pop = dma_counties.merge(
    county_pop[['county_DMA', 'state', '2022_pop']],
    left_on=['county', 'state'],
    right_on=['county_DMA', 'state'],
    how='left'
)

# Get unmatched counties
unmatched = dma_counties_with_pop[dma_counties_with_pop['2022_pop'].isna()].copy()

# Known split counties pattern
split_pattern = r'-(?:N|S|E|W|C|Ind|Plus|Rem|Pensla|Sustn|Dade)$'
unmatched['is_split'] = unmatched['county'].str.contains(split_pattern, regex=True, na=False)

# Separate split vs non-split
split_counties = unmatched[unmatched['is_split']]
non_split_unmatched = unmatched[~unmatched['is_split']]

print("=" * 80)
print("UNMATCHED COUNTIES ANALYSIS")
print("=" * 80)

print(f"\nTotal unmatched: {len(unmatched)}")
print(f"Split counties (expected): {len(split_counties)}")
print(f"Non-split unmatched (need investigation): {len(non_split_unmatched)}")

if len(non_split_unmatched) > 0:
    print("\n" + "=" * 80)
    print("NON-SPLIT UNMATCHED COUNTIES")
    print("=" * 80)
    print(non_split_unmatched[['county', 'state']].sort_values(['state', 'county']).to_string(index=False))

    # For each unmatched county, search for similar names in county_pop
    print("\n" + "=" * 80)
    print("SEARCHING FOR SIMILAR NAMES IN COUNTY POPULATION FILE")
    print("=" * 80)

    for _, row in non_split_unmatched.iterrows():
        county_name = row['county']
        state = row['state']

        # Skip if county_name or state is NaN
        if pd.isna(county_name) or pd.isna(state):
            continue

        # Search for counties in the same state in county_pop
        same_state = county_pop[county_pop['state'] == state]

        # Case-insensitive search for similar names
        county_lower = county_name.lower()
        similar = same_state[same_state['county_DMA'].str.lower().str.contains(county_lower[:5], na=False) |
                            same_state['county_DMA'].str.lower().str.contains(county_lower[-5:], na=False)]

        if len(similar) > 0:
            print(f"\n{county_name}, {state}:")
            print(f"  Possible matches in county_pop:")
            for _, match in similar.iterrows():
                print(f"    - {match['county_DMA']}")
        else:
            # Try just looking at all counties in that state
            print(f"\n{county_name}, {state}:")
            print(f"  No obvious matches. All {state} counties in county_pop:")
            for _, match in same_state.iterrows():
                print(f"    - {match['county_DMA']}")

print("\n" + "=" * 80)
print("CHECKING CASE-SENSITIVITY ISSUES")
print("=" * 80)

# Check if case-insensitive matching would help
dma_counties_lower = dma_counties.copy()
dma_counties_lower['county_lower'] = dma_counties_lower['county'].str.lower()
dma_counties_lower['state_lower'] = dma_counties_lower['state'].str.lower()

county_pop_lower = county_pop.copy()
county_pop_lower['county_DMA_lower'] = county_pop_lower['county_DMA'].str.lower()
county_pop_lower['state_lower'] = county_pop_lower['state'].str.lower()

# Case-insensitive merge
case_insensitive_match = dma_counties_lower.merge(
    county_pop_lower[['county_DMA_lower', 'state_lower', 'county_DMA']],
    left_on=['county_lower', 'state_lower'],
    right_on=['county_DMA_lower', 'state_lower'],
    how='left'
)

# Find counties that match case-insensitively but not case-sensitively
case_issues = case_insensitive_match[
    (case_insensitive_match['county_DMA'].notna()) &  # Matches case-insensitively
    (case_insensitive_match['county'] != case_insensitive_match['county_DMA'])  # Different case
]

if len(case_issues) > 0:
    print(f"\nFound {len(case_issues)} counties with case-sensitivity issues:")
    print("\nZIP to DMA -> County Pop (case mismatch):")
    for _, row in case_issues[['county', 'county_DMA', 'state']].drop_duplicates().iterrows():
        print(f"  '{row['county']}' -> '{row['county_DMA']}' ({row['state']})")
else:
    print("\nNo case-sensitivity issues found.")
