# Author: Hannah Lybbert
# Created: 01/28/2026
# Updated: 01/29/2026
# Purpose: Creating crosswalk from Comscore metro areas and states (Git Issue #12)


'''
Work flow:
    (1) Map DMA --> counties
        - each DMA has a dozen or so counties 
        - For each DMA
            - find out which counties are in that DMA (Nielsen data)
            - find out which states the counties are from (Nielsen)
            - find the population of each county (census county pop file, use 2022 pops)
            - find the share of the DMA population from each state 
                - DMA population = aggregate pops of counties within DMA
                - State 1 share = aggregate county pops from State 1 / DMA population
                - State 2 share = aggregate county pops from State 2 / DMA population


    (2) Map DMA --> states
        - Set threshold for including/excluding
            - If share of minority state is below certain threshold --> majority state becomes DMA state
            - If share of minority state is above certain threshold --> drop DMA from analaysis

Input files:
    "\\data\\ProcessAuxiliary\\DMA_County\\raw\\Zip to DMA 2023.XLS"
    "\\data\\ProcessAuxiliary\\DMA_County\\raw\\co-est2024-pop.xlsx"

Output file:
    "\\data\\ProcessAuxiliary\\DMA_County\\DMA_state_crosswalk.csv"
    210 rows for 210 metro areas
    7 columns (DMA code, DMA name, state 1 share, state 2 share, state 3 share, Majority State name, include (1 if include, 0 if exclude)
'''

import pandas as pd
import numpy as np
import os

# Set working directory
# os.chdir(r"C:\Users\hlybbert\OneDrive - The University of Chicago\Documents\AgeVerification")

# Get the project root directory (3 levels up from this file)
file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(file_dir, "..", "..", ".."))

# Read input files
print("Reading input files...")
zip_dma = pd.read_csv(os.path.join(project_root, "data", "ProcessAuxiliary", "DMA_County", "ZIP_to_DMA_clean.csv"))
county_pop = pd.read_csv(os.path.join(project_root, "data", "ProcessAuxiliary", "DMA_County", "co_est2022_pop_standardized.csv"))

# Filter out any rows with NaN county or state (e.g., metadata/copyright rows)
zip_dma = zip_dma.dropna(subset=['county', 'state'])

print(f"ZIP to DMA file: {len(zip_dma):,} rows")
print(f"County population file: {len(county_pop):,} rows")
print(f"Unique DMAs: {zip_dma['DMA_code'].nunique()}")

# ============================================================================
# STEP 1: Map DMA --> Counties and Calculate State Shares
# ============================================================================

print("\n" + "=" * 80)
print("STEP 1: Calculating state shares within each DMA")
print("=" * 80)

# Get unique county-state-DMA combinations from ZIP to DMA file
dma_counties = zip_dma[['DMA_code', 'DMA_name', 'county', 'state']].drop_duplicates()

print(f"\nUnique DMA-county-state combinations: {len(dma_counties):,}")

# Merge with county population data
# Match on county (from ZIP to DMA) = county_DMA (from population file) and state
dma_counties_pop = dma_counties.merge(
    county_pop[['county_DMA', 'state', '2022_pop']],
    left_on=['county', 'state'],
    right_on=['county_DMA', 'state'],
    how='left'
)

# Check for counties that didn't match
unmatched = dma_counties_pop[dma_counties_pop['2022_pop'].isna()]
print(f"\nCounties without population data: {len(unmatched)}")
if len(unmatched) > 0:
    print("\nFirst 10 unmatched counties:")
    print(unmatched[['county', 'state', 'DMA_name']].head(10).to_string(index=False))

# Drop unmatched counties (these are the split counties we identified earlier)
dma_counties_pop = dma_counties_pop[dma_counties_pop['2022_pop'].notna()]

print(f"\nCounties with population data: {len(dma_counties_pop):,}")

# Calculate DMA total population and state shares
print("\nCalculating state shares for each DMA...")

# For each DMA, calculate total population
dma_total_pop = dma_counties_pop.groupby(['DMA_code', 'DMA_name']).agg({
    '2022_pop': 'sum'
}).rename(columns={'2022_pop': 'DMA_total_pop'}).reset_index()

# For each DMA-state combination, calculate state population within DMA
dma_state_pop = dma_counties_pop.groupby(['DMA_code', 'DMA_name', 'state']).agg({
    '2022_pop': 'sum',
    'county': 'count'  # Count of counties from this state in this DMA
}).rename(columns={'2022_pop': 'state_pop_in_DMA', 'county': 'num_counties'}).reset_index()

# Merge to get DMA total population
dma_state_pop = dma_state_pop.merge(dma_total_pop, on=['DMA_code', 'DMA_name'])

# Calculate state share
dma_state_pop['state_share'] = dma_state_pop['state_pop_in_DMA'] / dma_state_pop['DMA_total_pop']

print(f"\nDMAs with population data: {dma_state_pop['DMA_code'].nunique()}")

# Display summary statistics
print("\n" + "=" * 80)
print("SUMMARY STATISTICS")
print("=" * 80)

# Count states per DMA
states_per_dma = dma_state_pop.groupby('DMA_code')['state'].count().reset_index()
states_per_dma.columns = ['DMA_code', 'num_states']

print("\nStates per DMA distribution:")
print(states_per_dma['num_states'].value_counts().sort_index())

# Show examples
print("\n" + "=" * 80)
print("EXAMPLE: DMAs with Multiple States")
print("=" * 80)

# Find DMAs with multiple states
multi_state_dmas = dma_state_pop[dma_state_pop['DMA_code'].isin(
    states_per_dma[states_per_dma['num_states'] > 1]['DMA_code']
)]

# Show a few examples
example_dmas = multi_state_dmas['DMA_code'].unique()[:5]
for dma_code in example_dmas:
    dma_data = dma_state_pop[dma_state_pop['DMA_code'] == dma_code].copy()
    dma_data = dma_data.sort_values('state_share', ascending=False)

    print(f"\n{dma_data.iloc[0]['DMA_name']} (DMA {dma_code}):")
    print(f"  Total DMA population: {dma_data.iloc[0]['DMA_total_pop']:,.0f}")
    for _, row in dma_data.iterrows():
        print(f"  - {row['state']}: {row['state_share']*100:.1f}% ({row['num_counties']} counties, pop: {row['state_pop_in_DMA']:,.0f})")

# Save intermediate results
output_file = os.path.join(project_root, "data", "ProcessAuxiliary", "DMA_County", "DMA_state_shares.csv")
dma_state_pop.to_csv(output_file, index=False)
print(f"\n\nIntermediate results saved to: {output_file}")

# ============================================================================
# Calculate Majority State and Minority Share for Each DMA
# ============================================================================

print("\n" + "=" * 80)
print("CALCULATING MAJORITY STATE AND MINORITY SHARE")
print("=" * 80)

# For each DMA, find the state with the maximum share
majority_state = dma_state_pop.loc[dma_state_pop.groupby('DMA_code')['state_share'].idxmax()]
majority_state = majority_state[['DMA_code', 'DMA_name', 'state', 'state_share', 'DMA_total_pop']].rename(
    columns={'state': 'majority_state', 'state_share': 'majority_share'}
)

# Calculate minority share (1 - majority_share)
majority_state['minority_share'] = 1 - majority_state['majority_share']

# Count number of states per DMA
states_count = dma_state_pop.groupby('DMA_code')['state'].count().reset_index()
states_count.columns = ['DMA_code', 'num_states']

# Merge
dma_summary = majority_state.merge(states_count, on='DMA_code')

print(f"\nDMAs with majority state calculated: {len(dma_summary)}")

# Display summary statistics
print("\nMinority share distribution:")
print(dma_summary['minority_share'].describe())

print("\nExamples:")
print("\nSingle-state DMAs (minority_share = 0):")
single_state = dma_summary[dma_summary['num_states'] == 1].head(5)
for _, row in single_state.iterrows():
    print(f"  {row['DMA_name']}: {row['majority_state']} (100%)")

print("\nMulti-state DMAs (sorted by minority share):")
multi_state = dma_summary[dma_summary['num_states'] > 1].sort_values('minority_share', ascending=False).head(10)
for _, row in multi_state.iterrows():
    print(f"  {row['DMA_name']}: {row['majority_state']} {row['majority_share']*100:.1f}% | "
          f"Minority: {row['minority_share']*100:.1f}% ({row['num_states']} states)")

# Save DMA summary
summary_output = os.path.join(project_root, "data", "ProcessAuxiliary", "DMA_County", "DMA_summary.csv")
dma_summary.to_csv(summary_output, index=False)
print(f"\nDMA summary saved to: {summary_output}")

print("\n" + "=" * 80)
print("STEP 1 COMPLETE")
print("=" * 80)
print(f"DMAs analyzed: {dma_state_pop['DMA_code'].nunique()}")
print(f"Total DMA-state combinations: {len(dma_state_pop)}")
print(f"DMAs with majority state calculated: {len(dma_summary)}")

'''
CLAUDE CODE PSEUDO CODE:

  # STEP 1: Map DMA --> Counties and Calculate State Shares
  # =======================================================

  FOR each DMA (metro area):

      # Get county composition
      counties_in_dma = get_counties_from_nielsen_data(dma)

      # Get state and population for each county
      FOR each county in counties_in_dma:
          state = get_state_for_county(county, nielsen_data)
          population = get_county_population(county, census_2022_data)
          store (county, state, population)

      # Calculate DMA total population
      dma_total_population = SUM(all county populations in dma)

      # Calculate state shares within DMA
      state_shares = {}
      FOR each unique state in dma:
          state_population_in_dma = SUM(county populations for that state)
          state_share = state_population_in_dma / dma_total_population
          state_shares[state] = state_share


  # STEP 2: Map DMA --> States (Apply Threshold Logic)
  # ===================================================

  SET threshold = [some percentage, e.g., 0.10 or 0.05]

  FOR each DMA with calculated state_shares:

      majority_state = state with highest share
      minority_states = all other states

      IF all minority_state_shares < threshold:
          # Single dominant state
          assign_dma_to_state = majority_state
          include_in_analysis = 1

      ELSE:
          # Significant multi-state presence
          assign_dma_to_state = NULL (or keep all states listed)
          include_in_analysis = 0

      # Store results
      OUTPUT: (dma_code, dma_name, state_1_share, state_2_share,
               state_3_share, majority_state, include_in_analysis)


  # FINAL OUTPUT
  # ============
  Write to: "\\data\\ProcessAuxiliary\\DMA_County\\DMA_state_crosswalk.csv"
      - 210 rows (one per DMA)
      - Columns: DMA code, DMA name, state 1 share, state 2 share,
                 state 3 share, Majority State name, include (1/0)

'''
