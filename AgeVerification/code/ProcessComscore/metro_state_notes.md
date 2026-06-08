# Author: Hannah Lybbert
# Created: 01/28/2026
# Updated: 01/28/2026
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
    "\data\metro_state_crosswalk\process\Zip to DMA 2023.XLS"
    "\data\metro_state_crosswalk\process\co-est2024-pop.xlsx"

Output file:
    "\data\metro_state_crosswalk\DMA_state_crosswalk.csv"
    210 rows for 210 metro areas
    7 columns (DMA code, DMA name, state 1 share, state 2 share, state 3 share, Majority State name, include (1 if include, 0 if exclude)
'''









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
  Write to: "\data\metro_state_crosswalk\DMA_state_crosswalk.csv"
      - 210 rows (one per DMA)
      - Columns: DMA code, DMA name, state 1 share, state 2 share,
                 state 3 share, Majority State name, include (1/0)

'''
