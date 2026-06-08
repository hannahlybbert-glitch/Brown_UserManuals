# Author: Hannah Lybbert
# Created: 01/28/2026
# Updated: 01/29/2026
# Purpose: Standardize county population file to match ZIP to DMA county naming conventions (Git Issue #12)
# NOTE: Connecticut planning region to county mappings are APPROXIMATE

import pandas as pd
import os
import unicodedata

# Set working directory - comment out for portability
# os.chdir(r"C:\Users\hlybbert\OneDrive - The University of Chicago\Documents\AgeVerification")

# Get the project root directory (3 levels up from this file)
file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(file_dir, "..", "..", ".."))

# Read the cleaned county population file
county_pop = pd.read_csv(os.path.join(project_root, "data", "ProcessAuxiliary", "DMA_County", "co_est2022_pop_clean.csv"))

print(f"Original county population file: {len(county_pop)} rows")

# Function to remove accents from text
def remove_accents(text):
    if pd.isna(text):
        return text
    # Normalize to NFD (decomposed form) and filter out combining characters
    nfd_form = unicodedata.normalize('NFD', str(text))
    return ''.join([char for char in nfd_form if unicodedata.category(char) != 'Mn'])

# Apply transformations to match ZIP to DMA format
def standardize_county_name(county_name):
    if pd.isna(county_name):
        return county_name

    # Remove accents (e.g., Doña → Dona)
    county_name = remove_accents(county_name)

    # Remove periods from St. and Ste. (St. → St, Ste. → Ste)
    county_name = county_name.replace('St. ', 'St ')
    county_name = county_name.replace('Ste. ', 'Ste ')

    # Remove apostrophes (St. Mary's → St Marys, Queen Anne's → Queen Annes, O'Brien → Obrien)
    county_name = county_name.replace("'s", 's')
    county_name = county_name.replace("'", '')

    # Abbreviate directional words at the BEGINNING of county names
    # East → E, West → W, North → N, South → S
    directional_replacements = {
        'East ': 'E ',
        'West ': 'W ',
        'North ': 'N ',
        'South ': 'S '
    }

    for full, abbrev in directional_replacements.items():
        if county_name.startswith(full):
            county_name = abbrev + county_name[len(full):]
            break

    # Handle capitalization patterns to match ZIP to DMA format
    # McKean → Mckean, DeKalb → Dekalb, DeSoto → Desoto, LaPorte → Laporte, etc.
    import re

    # Mc[Capital letter] → Mc[lowercase]
    county_name = re.sub(r'\bMc([A-Z])', lambda m: 'Mc' + m.group(1).lower(), county_name)

    # De[Capital letter] → De[lowercase] (at word boundaries)
    county_name = re.sub(r'\bDe([A-Z])', lambda m: 'De' + m.group(1).lower(), county_name)

    # La[Capital letter] → La[lowercase]
    county_name = re.sub(r'\bLa([A-Z])', lambda m: 'La' + m.group(1).lower(), county_name)

    # Du[Capital letter] → Du[lowercase]
    county_name = re.sub(r'\bDu([A-Z])', lambda m: 'Du' + m.group(1).lower(), county_name)

    # " of " → " Of " (capitalize "of" in county names)
    county_name = re.sub(r'\bof\b', 'Of', county_name)

    # " du " → " Du " (capitalize "du" in county names like "Fond du Lac")
    county_name = re.sub(r'\bdu\b', 'Du', county_name)

    # " qui " → " Qui " (for Lac qui Parle)
    county_name = re.sub(r'\bqui\b', 'Qui', county_name)

    return county_name

# Create the county_DMA column by applying standardization to county_name
county_pop['county_DMA'] = county_pop['county_name'].apply(standardize_county_name)

# Apply specific manual mappings for known abbreviations/typos in ZIP to DMA file
# These are based on the comparison analysis
manual_mappings = {
    ('Baltimore city', 'MD'): 'Baltimre City',
    ('Chesapeake city', 'VA'): 'Chspeake City',
    ('Cape Girardeau', 'MO'): 'Cpe Girardeau',
    ('District Of Columbia', 'DC'): 'Dis Of Col',  # After "of" → "Of" transformation
    ('Hampton city', 'VA'): 'Hampton City',
    ('Newport News city', 'VA'): 'Nwprt Nws Cty',
    ('Norfolk city', 'VA'): 'Norfolk City',
    ('Virginia Beach city', 'VA'): 'Virginia Bch',
    ('Portsmouth city', 'VA'): 'Prtsmuth City',
    ('Suffolk city', 'VA'): 'Suffolk City',
    ('Blue Earth', 'MN'): 'Bl Erth-Ncl-S',
    ('Nicollet', 'MN'): 'Nicollet-N',
    ('St Louis', 'MO'): 'St Louis',  # St Louis County
    ('St Louis city', 'MO'): 'St Louis-Ind',  # St Louis City
    ('Miami', 'FL'): 'Miami-Dade',
    ('Santa Barbara', 'CA'): 'Santa Brbra',  # Abbreviated in DMA
    ('Matanuska-Susitna', 'AK'): 'Matanka-Sustn',  # Census doesn't have "Borough"
    ('Kenai Peninsula', 'AK'): 'Kenai-Pensla',  # Census doesn't have "Borough"
    ('Juneau City and', 'AK'): 'Juneau-Plus',  # Census name is truncated
    ('Grand Traverse', 'MI'): 'Gr Traverse',
    ('King and Queen', 'VA'): 'Kng And Queen',
    ('Prince William', 'VA'): 'Prince Wm',
    ('Queen Annes', 'MD'): 'Queen Annes',
    ('San Bernardino', 'CA'): 'San Bernardno',
    ('San Luis Obispo', 'CA'): 'San Luis Obpo',
    ('Yellow Medicine', 'MN'): 'Yellow Med',
    ('St John the Baptist', 'LA'): 'St John Bapt',
    ('Jefferson Davis', 'LA'): 'Jeff Davis',
    ('Jefferson Davis', 'MS'): 'Jeff Davis',
    ('Lewis and Clark', 'MT'): 'Lwis And Clrk',
    ('E Carroll', 'LA'): 'East Carroll',
    ('W Carroll', 'LA'): 'West Carroll',
    ('Lasalle', 'IL'): 'La Salle',  # After La[A-Z] → La[lowercase] transformation
    ('Lasalle', 'LA'): 'La Salle',  # After La[A-Z] → La[lowercase] transformation
    ('Lasalle', 'TX'): 'La Salle',  # After La[A-Z] → La[lowercase] transformation
    ('OBrien', 'IA'): 'Obrien',  # After apostrophe removal, O'Brien → OBrien → Obrien
    ('Lake Of the Woods', 'MN'): 'Lake Of Woods',  # After "of" → "Of" transformation
    ('Northumberland', 'PA'): 'Northumberlnd',
    ('Northumberland', 'VA'): 'Northumberlnd',
    ('Prince Georges', 'MD'): 'Prince George',
    ('Richmond city', 'VA'): 'Richmond-Ind',  # Richmond city → Richmond-Ind (Richmond County stays as Richmond)
}

# Apply manual mappings
for (county, state), new_name in manual_mappings.items():
    mask = (county_pop['county_DMA'] == county) & (county_pop['state'] == state)
    county_pop.loc[mask, 'county_DMA'] = new_name

# Connecticut Planning Region to County Mapping (APPROXIMATE)
# NOTE: These mappings are approximate and aggregate planning region populations to counties
ct_planning_to_county = {
    'Northwest Hills Planning Region': ['Litchfield'],
    'Greater Bridgeport Planning Region': ['Fairfield'],
    'Western Connecticut Planning Region': ['Fairfield'],
    'Naugatuck Valley Planning Region': ['New Haven'],
    'South Central Connecticut Planning Region': ['New Haven'],
    'Lower Connecticut River Valley Planning Region': ['Middlesex'],
    'Capitol Planning Region': ['Hartford', 'Tolland'],  # Both Hartford and Tolland are in Hartford & New Haven DMA
    'Southeastern Connecticut Planning Region': ['New London'],
    'Northeastern Connecticut Planning Region': ['Windham'],
}

# Process Connecticut planning regions
ct_rows = []
for idx, row in county_pop[county_pop['state'] == 'CT'].iterrows():
    planning_region = row['county_name']

    if planning_region in ct_planning_to_county:
        counties = ct_planning_to_county[planning_region]
        population = row['2022_pop']

        # Create a row for each county this planning region maps to
        for county in counties:
            ct_rows.append({
                'county_name': planning_region,
                'county_DMA': county,
                'state': 'CT',
                '2022_pop': population
            })

# Remove original Connecticut planning region rows
county_pop = county_pop[county_pop['state'] != 'CT']

# Add the new Connecticut county rows
if ct_rows:
    ct_df = pd.DataFrame(ct_rows)
    county_pop = pd.concat([county_pop, ct_df], ignore_index=True)

# Aggregate Connecticut counties that have multiple planning regions mapping to them
# (e.g., Fairfield gets Greater Bridgeport + Western Connecticut)
ct_aggregated = county_pop[county_pop['state'] == 'CT'].groupby(['county_DMA', 'state']).agg({
    'county_name': lambda x: ' + '.join(sorted(set(x))),  # Combine planning region names
    '2022_pop': 'sum'  # Sum the populations
}).reset_index()

# Remove non-aggregated CT rows and add aggregated ones
county_pop = county_pop[county_pop['state'] != 'CT']
county_pop = pd.concat([county_pop, ct_aggregated], ignore_index=True)

# ============================================================================
# Handle Split Counties (N/S/E/W/C) and Special Cases
# ============================================================================
print("\n" + "=" * 80)
print("HANDLING SPLIT COUNTIES AND SPECIAL CASES")
print("=" * 80)

# Read DMA data to identify split counties
zip_dma = pd.read_csv(os.path.join("data", "ProcessAuxiliary", "DMA_County", "ZIP_to_DMA_clean.csv"))

# Identify directional split counties only (N/S/E/W/C)
directional_split_pattern = r'-(?:N|S|E|W|C)$'
split_counties_dma = zip_dma[zip_dma['county'].str.contains(directional_split_pattern, regex=True, na=False)]
split_counties_unique = split_counties_dma[['county', 'state']].drop_duplicates()
split_counties_unique['base_county'] = split_counties_unique['county'].str.replace(directional_split_pattern, '', regex=True)

# Group by base county and state to get all splits
split_mapping = split_counties_unique.groupby(['base_county', 'state']).agg({
    'county': lambda x: list(x)
}).reset_index()
split_mapping['num_splits'] = split_mapping['county'].apply(len)
split_mapping = split_mapping.rename(columns={'county': 'split_names'})

print(f"\nDirectional splits (N/S/E/W/C):")
print(f"Found {len(split_mapping)} base counties with directional splits")

# Create new rows for directional split counties
split_rows = []
counties_to_remove = []

for _, split_info in split_mapping.iterrows():
    base_county = split_info['base_county']
    state = split_info['state']
    split_names = split_info['split_names']
    num_splits = split_info['num_splits']

    # Find matching census county
    matching_census = county_pop[
        (county_pop['county_DMA'] == base_county) &
        (county_pop['state'] == state)
    ]

    if len(matching_census) == 1:
        original_row = matching_census.iloc[0]
        original_pop = original_row['2022_pop']
        split_pop = original_pop / num_splits

        for split_name in split_names:
            split_rows.append({
                'county_name': original_row['county_name'],
                'county_DMA': split_name,
                'state': state,
                '2022_pop': split_pop
            })

        counties_to_remove.append((base_county, state))
        print(f"  {base_county}, {state}: Split {num_splits} ways - {split_names} ({original_pop:,.0f} ÷ {num_splits} = {split_pop:,.0f} each)")

# Handle Monroe County, NY special split
print("\nSpecial Monroe County, NY split:")
monroe_match = county_pop[(county_pop['county_DMA'] == 'Monroe') & (county_pop['state'] == 'NY')]
if len(monroe_match) == 1:
    monroe_row = monroe_match.iloc[0]
    monroe_pop = monroe_row['2022_pop']
    half_pop = monroe_pop / 2

    split_rows.append({
        'county_name': monroe_row['county_name'],
        'county_DMA': 'Monroe-Rem',
        'state': 'NY',
        '2022_pop': half_pop
    })
    split_rows.append({
        'county_name': monroe_row['county_name'],
        'county_DMA': 'Rochestr City',  # DMA uses abbreviated spelling
        'state': 'NY',
        '2022_pop': half_pop
    })

    counties_to_remove.append(('Monroe', 'NY'))
    print(f"  Monroe, NY: Split into Monroe-Rem and Rochester City ({monroe_pop:,.0f} ÷ 2 = {half_pop:,.0f} each)")

# Handle aggregations
print("\nAggregations:")

# Fairbanks aggregation: Fairbanks North Star + Southeast Fairbanks Census Area → Fairbanks-Plus
fairbanks_nsb = county_pop[(county_pop['county_name'] == 'Fairbanks North Star') & (county_pop['state'] == 'AK')]
fairbanks_se = county_pop[(county_pop['county_name'] == 'Southeast Fairbanks Census Area') & (county_pop['state'] == 'AK')]
if len(fairbanks_nsb) == 1 and len(fairbanks_se) == 1:
    total_pop = fairbanks_nsb.iloc[0]['2022_pop'] + fairbanks_se.iloc[0]['2022_pop']
    split_rows.append({
        'county_name': 'Fairbanks North Star Borough + Southeast Fairbanks Census Area',
        'county_DMA': 'Fairbnks-Plus',  # DMA uses abbreviated spelling
        'state': 'AK',
        '2022_pop': total_pop
    })
    # Mark for removal by county_name since these haven't been fully standardized yet
    county_pop = county_pop[
        ~((county_pop['county_name'] == 'Fairbanks North Star') & (county_pop['state'] == 'AK'))
    ]
    county_pop = county_pop[
        ~((county_pop['county_name'] == 'Southeast Fairbanks Census Area') & (county_pop['state'] == 'AK'))
    ]
    print(f"  Fairbanks-Plus, AK: Aggregated ({fairbanks_nsb.iloc[0]['2022_pop']:,.0f} + {fairbanks_se.iloc[0]['2022_pop']:,.0f} = {total_pop:,.0f})")

# Remove original counties that were split
for base_county, state in counties_to_remove:
    county_pop = county_pop[
        ~((county_pop['county_DMA'] == base_county) & (county_pop['state'] == state))
    ]

# Add all new split/aggregated rows
if split_rows:
    split_df = pd.DataFrame(split_rows)
    county_pop = pd.concat([county_pop, split_df], ignore_index=True)
    print(f"\nTotal: Added {len(split_rows)} new rows, removed {len(counties_to_remove)} original rows")

# Reorder columns
county_pop = county_pop[['county_name', 'county_DMA', 'state', '2022_pop']]

# Save the standardized file
output_file = os.path.join(project_root, "data", "ProcessAuxiliary", "DMA_County", "co_est2022_pop_standardized.csv")
county_pop.to_csv(output_file, index=False)

print(f"\nStandardized county population file saved to: {output_file}")
print(f"Number of rows: {len(county_pop)}")
print(f"Number of columns: {len(county_pop.columns)}")
print("\nFirst few rows:")
print(county_pop.head(10))

# Show examples of transformations
print("\n" + "=" * 80)
print("EXAMPLES OF TRANSFORMATIONS")
print("=" * 80)
print("\nConnecticut (planning regions aggregated to counties):")
print(county_pop[county_pop['state'] == 'CT'].sort_values('county_DMA'))
print("\nDirectional abbreviations (Louisiana):")
print(county_pop[county_pop['state'] == 'LA'].head(10))
print("\nAccent removal (New Mexico):")
print(county_pop[(county_pop['state'] == 'NM')].head(10))
print("\nManual mappings (Maryland, Virginia, DC):")
print(county_pop[county_pop['state'].isin(['MD', 'VA', 'DC'])].head(15))
print("\nSplit counties (examples):")
split_examples = county_pop[county_pop['county_DMA'].str.contains(r'-(?:N|S|E|W|C)$', regex=True, na=False)]
if len(split_examples) > 0:
    print(split_examples.head(15))
print("\nAggregations and special cases (AK, MO, NY):")
special_examples = county_pop[county_pop['state'].isin(['AK', 'MO', 'NY'])]
if len(special_examples) > 0:
    print(special_examples[special_examples['county_DMA'].str.contains('Plus|Ind|Rem|Pensla|Sustn', na=False)])
