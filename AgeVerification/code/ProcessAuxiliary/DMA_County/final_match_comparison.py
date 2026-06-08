# Author: Hannah Lybbert
# Created: 01/28/2026
# Updated: 01/29/2026
# Purpose: Final comparison of county matches after standardization (Git Issue #12)

import pandas as pd
import os

# Set working directory - comment out for portability
# os.chdir(r"C:\Users\hlybbert\OneDrive - The University of Chicago\Documents\AgeVerification")

# Get the project root directory (3 levels up from this file)
file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(file_dir, "..", "..", ".."))

# Read both files
zip_dma = pd.read_csv(os.path.join(project_root, "data", "ProcessAuxiliary", "DMA_County", "ZIP_to_DMA_clean.csv"))
county_pop_standardized = pd.read_csv(os.path.join(project_root, "data", "ProcessAuxiliary", "DMA_County", "co_est2022_pop_standardized.csv"))

print("=" * 80)
print("FINAL MATCH COMPARISON (AFTER STANDARDIZATION)")
print("=" * 80)

# Get unique county-state combinations
zip_dma_counties = zip_dma[['county', 'state']].dropna().drop_duplicates()
county_pop_counties = county_pop_standardized[['county_DMA', 'state']].dropna().drop_duplicates()
county_pop_counties = county_pop_counties.rename(columns={'county_DMA': 'county'})

print(f"\nUnique county-state combinations in ZIP to DMA: {len(zip_dma_counties)}")
print(f"Unique county-state combinations in County Pop (standardized): {len(county_pop_counties)}")

# Create keys for matching (case-insensitive)
zip_dma_counties['key'] = (zip_dma_counties['county'].str.lower() + '|' +
                            zip_dma_counties['state'].str.lower())
county_pop_counties['key'] = (county_pop_counties['county'].str.lower() + '|' +
                               county_pop_counties['state'].str.lower())

# Find matches and mismatches
zip_keys = set(zip_dma_counties['key'])
pop_keys = set(county_pop_counties['key'])

matches = zip_keys & pop_keys
in_zip_not_pop = zip_keys - pop_keys
in_pop_not_zip = pop_keys - zip_keys

print(f"\n" + "=" * 80)
print("MATCHING RESULTS")
print("=" * 80)
print(f"\nMatching counties: {len(matches)}")
print(f"Counties in ZIP to DMA but NOT in County Pop: {len(in_zip_not_pop)}")
print(f"Counties in County Pop but NOT in ZIP to DMA: {len(in_pop_not_zip)}")

match_percentage = (len(matches) / len(zip_keys)) * 100 if len(zip_keys) > 0 else 0
print(f"\nMatch percentage: {match_percentage:.1f}%")

# Show remaining mismatches
if len(in_zip_not_pop) > 0:
    print(f"\n" + "=" * 80)
    print("COUNTIES IN ZIP TO DMA BUT NOT IN COUNTY POP")
    print("=" * 80)
    print(f"\nTotal: {len(in_zip_not_pop)}")
    print("\nAll mismatches:")
    for key in sorted(in_zip_not_pop):
        county, state = key.split('|')
        print(f"  {county}, {state}")

if len(in_pop_not_zip) > 0:
    print(f"\n" + "=" * 80)
    print("COUNTIES IN COUNTY POP BUT NOT IN ZIP TO DMA")
    print("=" * 80)
    print(f"\nTotal: {len(in_pop_not_zip)}")

    # Create a dataframe with the unmatched counties and their populations
    unmatched_list = []
    for key in in_pop_not_zip:
        county, state = key.split('|')
        # Get population for this county
        pop_data = county_pop_standardized[
            (county_pop_standardized['county_DMA'].str.lower() == county) &
            (county_pop_standardized['state'].str.lower() == state)
        ]
        if len(pop_data) > 0:
            pop = pop_data.iloc[0]['2022_pop']
            county_name = pop_data.iloc[0]['county_name']
        else:
            pop = 0
            county_name = county

        unmatched_list.append({
            'county_DMA': county.title(),
            'county_name': county_name,
            'state': state.upper(),
            'population': pop
        })

    unmatched_df = pd.DataFrame(unmatched_list)

    # Categorize by type
    unmatched_df['type'] = 'County'
    unmatched_df.loc[unmatched_df['county_name'].str.contains('city', case=False, na=False), 'type'] = 'Independent City'
    unmatched_df.loc[unmatched_df['county_name'].str.contains('Census Area', case=False, na=False), 'type'] = 'Census Area'
    unmatched_df.loc[unmatched_df['county_name'].str.contains('Borough', case=False, na=False), 'type'] = 'Borough'

    # Group by state
    print("\n" + "-" * 80)
    print("BREAKDOWN BY STATE")
    print("-" * 80)
    state_summary = unmatched_df.groupby('state').agg({
        'county_DMA': 'count',
        'population': 'sum'
    }).rename(columns={'county_DMA': 'count'}).sort_values('count', ascending=False)

    for state, row in state_summary.iterrows():
        print(f"{state}: {row['count']} counties (total pop: {row['population']:,.0f})")

    # Group by type
    print("\n" + "-" * 80)
    print("BREAKDOWN BY TYPE")
    print("-" * 80)
    type_summary = unmatched_df.groupby('type').agg({
        'county_DMA': 'count',
        'population': 'sum'
    }).rename(columns={'county_DMA': 'count'}).sort_values('count', ascending=False)

    for type_name, row in type_summary.iterrows():
        print(f"{type_name}: {row['count']} ({row['population']:,.0f} total pop)")

    # Show all unmatched counties sorted by state and population
    print("\n" + "-" * 80)
    print("ALL UNMATCHED COUNTIES (sorted by state, then population)")
    print("-" * 80)
    unmatched_sorted = unmatched_df.sort_values(['state', 'population'], ascending=[True, False])

    current_state = None
    for _, row in unmatched_sorted.iterrows():
        if row['state'] != current_state:
            current_state = row['state']
            print(f"\n{current_state}:")
        print(f"  {row['county_DMA']:30} ({row['type']:20}) Pop: {row['population']:>10,.0f}")

print("\n" + "=" * 80)
print("EXCLUSIONS SUMMARY (for documentation)")
print("=" * 80)
print("\nThe following census counties are NOT in the DMA data and are excluded from analysis:")
print(f"\n  • {len(unmatched_df[unmatched_df['state'] == 'VA'])} Virginia independent cities")
print(f"    (These are legally separate from counties and not included in Nielsen DMA definitions)")
print(f"\n  • {len(unmatched_df[unmatched_df['state'] == 'AK'])} Alaska counties/census areas")
print(f"    (Remote areas not covered by Nielsen designated market areas)")
print(f"\n  • {len(unmatched_df[unmatched_df['state'] == 'HI'])} Hawaii county (Kalawao)")
print(f"    (Very small isolated area)")
print(f"\nTotal excluded: {len(unmatched_df)} counties/cities representing {unmatched_df['population'].sum():,.0f} people")
print(f"These exclusions do not affect DMA-to-state mapping as they are not part of any DMA.")

print("\n" + "=" * 80)
