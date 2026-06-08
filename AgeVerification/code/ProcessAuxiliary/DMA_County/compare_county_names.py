# Author: Hannah Lybbert
# Created: 01/28/2026
# Updated: 01/29/2026
# Purpose: Compare county names between ZIP to DMA file and county population file (Git Issue #12)

import pandas as pd
import os

# Set working directory - comment out for portability
# os.chdir(r"C:\Users\hlybbert\OneDrive - The University of Chicago\Documents\AgeVerification")

# Get the project root directory (3 levels up from this file)
file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(file_dir, "..", "..", ".."))

# Read both cleaned files
zip_dma = pd.read_csv(os.path.join(project_root, "data", "ProcessAuxiliary", "DMA_County", "ZIP_to_DMA_clean.csv"))
county_pop = pd.read_csv(os.path.join(project_root, "data", "ProcessAuxiliary", "DMA_County", "co_est2022_pop_clean.csv"))

print("=" * 80)
print("DATASET OVERVIEW")
print("=" * 80)
print(f"\nZIP to DMA file: {len(zip_dma)} rows")
print(f"County population file: {len(county_pop)} rows")

# Get unique county-state combinations from each file, excluding NaN values
zip_dma_counties = zip_dma[['county', 'state']].dropna().drop_duplicates()
county_pop_counties = county_pop[['county_name', 'state']].dropna().drop_duplicates()

print(f"\nUnique county-state combinations in ZIP to DMA: {len(zip_dma_counties)}")
print(f"Unique county-state combinations in County Pop: {len(county_pop_counties)}")

# Create a combined key for matching
zip_dma_counties['key'] = zip_dma_counties['county'] + '|' + zip_dma_counties['state']
county_pop_counties['key'] = county_pop_counties['county_name'] + '|' + county_pop_counties['state']

# Find counties in ZIP to DMA but not in County Pop
in_zip_not_pop = set(zip_dma_counties['key']) - set(county_pop_counties['key'])
# Find counties in County Pop but not in ZIP to DMA
in_pop_not_zip = set(county_pop_counties['key']) - set(zip_dma_counties['key'])

print("\n" + "=" * 80)
print("MISMATCHES")
print("=" * 80)

print(f"\nCounties in ZIP to DMA but NOT in County Pop: {len(in_zip_not_pop)}")
if len(in_zip_not_pop) > 0:
    print("\nFirst 20 examples:")
    for i, key in enumerate(sorted(in_zip_not_pop)[:20]):
        county, state = key.split('|')
        print(f"  {county}, {state}")

print(f"\n\nCounties in County Pop but NOT in ZIP to DMA: {len(in_pop_not_zip)}")
if len(in_pop_not_zip) > 0:
    print("\nFirst 20 examples:")
    for i, key in enumerate(sorted(in_pop_not_zip)[:20]):
        county, state = key.split('|')
        print(f"  {county}, {state}")

# Look for potential matches based on partial string matching
print("\n" + "=" * 80)
print("POTENTIAL MATCHES (Same state, similar county name)")
print("=" * 80)

# For each unmatched county in ZIP to DMA, look for similar names in County Pop in the same state
potential_matches = []
for zip_key in sorted(in_zip_not_pop):
    zip_county, zip_state = zip_key.split('|')

    # Look for counties in the same state in County Pop
    same_state_counties = county_pop_counties[county_pop_counties['state'] == zip_state]

    for _, row in same_state_counties.iterrows():
        pop_county = row['county_name']
        pop_key = row['key']

        # Check if this county is also unmatched
        if pop_key in in_pop_not_zip:
            # Look for partial matches or similar patterns
            if (zip_county.lower() in pop_county.lower() or
                pop_county.lower() in zip_county.lower() or
                zip_county.replace(' ', '').lower() == pop_county.replace(' ', '').lower()):
                potential_matches.append((zip_county, pop_county, zip_state))

if len(potential_matches) > 0:
    print(f"\nFound {len(potential_matches)} potential matches:")
    for zip_c, pop_c, state in potential_matches[:30]:
        print(f"  ZIP to DMA: '{zip_c}' <--> County Pop: '{pop_c}' (State: {state})")
else:
    print("\nNo obvious partial matches found.")

# Check for directional abbreviations (North -> N, South -> S, etc.)
print("\n" + "=" * 80)
print("CHECKING FOR DIRECTIONAL ABBREVIATIONS")
print("=" * 80)

directional_patterns = {
    'North ': 'N ',
    'South ': 'S ',
    'East ': 'E ',
    'West ': 'W '
}

directional_mismatches = []
for zip_key in sorted(in_zip_not_pop):
    zip_county, zip_state = zip_key.split('|')

    # Check if abbreviating directionals would create a match
    for full, abbrev in directional_patterns.items():
        if full in zip_county:
            abbreviated = zip_county.replace(full, abbrev)
            test_key = f"{abbreviated}|{zip_state}"
            if test_key in in_pop_not_zip:
                directional_mismatches.append((zip_county, abbreviated, zip_state))
        elif abbrev in zip_county:
            expanded = zip_county.replace(abbrev, full)
            test_key = f"{expanded}|{zip_state}"
            if test_key in in_pop_not_zip:
                directional_mismatches.append((zip_county, expanded, zip_state))

if len(directional_mismatches) > 0:
    print(f"\nFound {len(directional_mismatches)} directional abbreviation mismatches:")
    for zip_c, match_c, state in directional_mismatches[:30]:
        print(f"  ZIP to DMA: '{zip_c}' <--> Match: '{match_c}' (State: {state})")
else:
    print("\nNo directional abbreviation mismatches found.")

# Analyze split counties
print("\n" + "=" * 80)
print("SPLIT COUNTY ANALYSIS")
print("=" * 80)

# Identify split counties (counties with directional or other suffixes)
# Common patterns: -N, -S, -E, -W, -C, -Ind, -Plus, -Rem, -Pensla, etc.
split_pattern = r'-(?:N|S|E|W|C|Ind|Plus|Rem|Pensla|Sustn|Dade)$'
zip_dma_counties['is_split'] = zip_dma_counties['county'].str.contains(split_pattern, regex=True, na=False)

split_counties = zip_dma_counties[zip_dma_counties['is_split']]
print(f"\nNumber of unique split county-state combinations: {len(split_counties)}")
print(f"Percentage of unique counties that are split: {len(split_counties)/len(zip_dma_counties)*100:.1f}%")

# Count how many ZIP codes are in split counties vs regular counties
zip_dma['is_split_county'] = zip_dma['county'].str.contains(split_pattern, regex=True, na=False)
split_zips = zip_dma[zip_dma['is_split_county']]
print(f"\nNumber of ZIP codes in split counties: {len(split_zips):,}")
print(f"Percentage of ZIP codes in split counties: {len(split_zips)/len(zip_dma)*100:.1f}%")

# Show examples of split counties grouped by base name
print("\nExamples of split counties:")
split_counties_sorted = split_counties.sort_values(['state', 'county'])
for i, (_, row) in enumerate(split_counties_sorted.head(20).iterrows()):
    print(f"  {row['county']}, {row['state']}")

# Identify base counties (county name without the suffix)
split_counties['base_county'] = split_counties['county'].str.replace(split_pattern, '', regex=True)
base_county_counts = split_counties.groupby(['base_county', 'state']).size().reset_index(name='split_count')
base_county_counts = base_county_counts[base_county_counts['split_count'] > 1]

print(f"\nCounties that are split into multiple regions: {len(base_county_counts)}")
print("\nExamples of how counties are split:")
for _, row in base_county_counts.head(10).iterrows():
    base = row['base_county']
    state = row['state']
    count = row['split_count']
    # Get all the split versions
    split_versions = split_counties[(split_counties['base_county'] == base) &
                                   (split_counties['state'] == state)]['county'].tolist()
    print(f"  {base}, {state}: split into {count} regions - {', '.join(split_versions)}")

# Check which DMAs contain split counties
split_dmas = zip_dma[zip_dma['is_split_county']][['DMA_code', 'DMA_name']].drop_duplicates()
total_dmas = zip_dma[['DMA_code', 'DMA_name']].drop_duplicates()
print(f"\n\nDMAs with split counties: {len(split_dmas)} out of {len(total_dmas)} total DMAs")
print(f"Percentage of DMAs affected: {len(split_dmas)/len(total_dmas)*100:.1f}%")

print("\n" + "=" * 80)
