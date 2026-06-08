# Author: Hannah Lybbert
# Created: 02/02/2026
# Updated: 02/03/2026
# Purpose: Map DMA market names to ComScore market names

"""
DMA to ComScore Market Mapping Script

This script creates a mapping between DMA markets and ComScore markets.
The names are similar but not exactly the same, so we use fuzzy matching
to create an initial mapping that can be manually reviewed and corrected.
"""

import pandas as pd
import numpy as np
import os
from fuzzywuzzy import fuzz, process

# Set working directory - comment out for portability
# os.chdir(r"C:\Users\hlybbert\OneDrive - The University of Chicago\Documents\AgeVerification")

# Get the project root directory (3 levels up from this file)
file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(file_dir, "..", "..", ".."))

# File paths - now using absolute paths based on project root
dma_file = os.path.join(project_root, "data", "ProcessAuxiliary", "DMA_County", "DMA_summary.csv")
dma_state_shares_file = os.path.join(project_root, "data", "ProcessAuxiliary", "DMA_County", "DMA_state_shares.csv")

# Check for both .txt (local) and .txt.gz (cluster) versions of demographics file
demographics_file_base = os.path.join(project_root, "raw", "desktop_demographics", "US_comscore_machine_demos_202201.txt")
if os.path.exists(demographics_file_base):
    demographics_file = demographics_file_base
elif os.path.exists(demographics_file_base + ".gz"):
    demographics_file = demographics_file_base + ".gz"
else:
    raise FileNotFoundError(f"Could not find demographics file at {demographics_file_base} or {demographics_file_base}.gz")

output_dir = os.path.join(project_root, "data", "ProcessAuxiliary", "DMA_market_state")
output_file = os.path.join(output_dir, "DMA_comscore_check_mapping.csv")

# Create output directory if needed
os.makedirs(output_dir, exist_ok=True)

print("="*80)
print("Step 1: Loading DMA data")
print("="*80)

# Read DMA data
dma_df = pd.read_csv(dma_file)
print(f"Loaded {len(dma_df)} DMAs")
print(f"\nDMA columns: {list(dma_df.columns)}")
print(f"\nSample DMAs:")
print(dma_df[['DMA_code', 'DMA_name', 'majority_state']].head(10).to_string(index=False))

# Read DMA state shares to get all states per DMA
print("\nLoading DMA state shares...")
dma_state_shares = pd.read_csv(dma_state_shares_file)
print(f"Loaded {len(dma_state_shares)} DMA-state combinations")

# Create a dictionary mapping DMA_code to list of states
dma_states_dict = dma_state_shares.groupby('DMA_code')['state'].apply(list).to_dict()
print(f"\nExample - DMA 501 (New York) spans states: {dma_states_dict.get(501.0)}")
print(f"Example - DMA 511 (Washington DC) spans states: {dma_states_dict.get(511.0)}")

print("\n" + "="*80)
print("Step 2: Loading ComScore market data from demographics file")
print("="*80)

# Read demographics file - only need region column
# Column names: machine_id, country, region, time_zone_bias, computer_location,
#               hoh_age, hh_income, children_present, hh_size, month_id
column_names = ['machine_id', 'country', 'region', 'time_zone_bias', 'computer_location',
                'hoh_age', 'hh_income', 'children_present', 'hh_size', 'month_id']

print("Reading demographics file (this may take a moment)...")
demographics_df = pd.read_csv(
    demographics_file,
    sep='\t',
    header=None,
    names=column_names,
    usecols=['region']
)

# Remove quotes from region names
demographics_df['region'] = demographics_df['region'].str.replace('"', '')

# Get unique ComScore markets
comscore_markets = demographics_df['region'].unique()
comscore_markets_df = pd.DataFrame({'comscore_market_full': sorted(comscore_markets)})

# Parse ComScore market names to separate market name from state
# Format is typically "City, ST" where ST is the 2-letter state abbreviation
def parse_comscore_market(full_name):
    """Parse ComScore market name into market name and state"""
    if ', ' in full_name:
        parts = full_name.rsplit(', ', 1)  # Split from the right to handle cases like "Winston-Salem, NC"
        market_name = parts[0].strip()
        state = parts[1].strip() if len(parts) > 1 else ''
    else:
        market_name = full_name
        state = ''
    return market_name, state

comscore_markets_df[['comscore_market_name', 'comscore_state']] = comscore_markets_df['comscore_market_full'].apply(
    lambda x: pd.Series(parse_comscore_market(x))
)

print(f"Found {len(comscore_markets_df)} unique ComScore markets")
print(f"\nSample ComScore markets (parsed):")
print(comscore_markets_df[['comscore_market_name', 'comscore_state', 'comscore_market_full']].head(15).to_string(index=False))

print("\n" + "="*80)
print("Step 3: Matching DMA names to ComScore markets")
print("="*80)

def clean_name(name):
    """Clean market name for better matching"""
    # Remove parenthetical content
    if '(' in name:
        name = name.split('(')[0].strip()
    # Remove extra spaces
    name = ' '.join(name.split())
    return name

def find_best_match(dma_name, dma_states, comscore_markets_df, threshold=70):
    """
    Find the best matching ComScore market for a DMA name
    Uses market name for matching and considers state overlap

    Args:
        dma_name: Name of the DMA
        dma_states: List of states in this DMA
        comscore_markets_df: DataFrame with ComScore markets
        threshold: Minimum match score

    Returns: (best_match_row, match_score, match_method, state_match)
    """
    # Clean the DMA name
    clean_dma = clean_name(dma_name)

    # Get list of ComScore market names (without state)
    comscore_names = comscore_markets_df['comscore_market_name'].tolist()
    comscore_states = comscore_markets_df['comscore_state'].tolist()

    best_match_idx = None
    best_score = 0
    best_method = 'no_match'
    state_matched = False

    # Try exact match first (ignoring case)
    for idx, market_name in enumerate(comscore_names):
        if clean_dma.lower() == market_name.lower():
            state_match = comscore_states[idx] in dma_states
            return comscore_markets_df.iloc[idx], 100, 'exact', state_match

    # Try partial match
    for idx, market_name in enumerate(comscore_names):
        if clean_dma.lower() in market_name.lower() or market_name.lower() in clean_dma.lower():
            score = fuzz.ratio(clean_dma.lower(), market_name.lower())
            state_match = comscore_states[idx] in dma_states

            # Boost score if state matches
            adjusted_score = score + 10 if state_match else score

            if adjusted_score > best_score and score >= threshold:
                best_score = score  # Keep original score for reporting
                best_match_idx = idx
                best_method = 'partial'
                state_matched = state_match

    if best_match_idx is not None:
        return comscore_markets_df.iloc[best_match_idx], best_score, best_method, state_matched

    # Use fuzzy matching on all markets
    matches = process.extract(clean_dma, comscore_names, scorer=fuzz.token_sort_ratio, limit=5)

    for match_name, score in matches:
        if score >= threshold:
            idx = comscore_names.index(match_name)
            state_match = comscore_states[idx] in dma_states
            adjusted_score = score + 10 if state_match else score

            if adjusted_score > best_score:
                best_score = score
                best_match_idx = idx
                best_method = 'fuzzy'
                state_matched = state_match

    if best_match_idx is not None:
        return comscore_markets_df.iloc[best_match_idx], best_score, best_method, state_matched

    return None, 0, 'no_match', False

# Manual overrides: human-verified DMA -> ComScore market mappings.
# These take priority over automated fuzzy matching.
# NOTE: "Tri-Cities, TN-VA" -> "Johnson City-Kingsport, TN" is flagged as uncertain.
MANUAL_OVERRIDES = {
    "Portland-Auburn": "Portland, ME",
    "Cleveland-Akron (Canton)": "Cleveland, OH",
    "Washington, DC (Hagrstwn)": "Washington, DC",
    "Flint-Saginaw-Bay City": "Flint-Saginaw, MI",
    "Greensboro-H.Point-W.Salem": "Greensboro-Winston-Salem, NC",
    "Charleston, SC": "Charleston, SC",
    "Augusta-Aiken": "Augusta-Aiken, GA-SC",
    "Providence-New Bedford": "Providence, RI",
    "Columbus, GA (Opelika, AL)": "Columbus-Auburn, GA-AL",
    "Burlington-Plattsburgh": "Burlington-Plattsburgh, VT-NY",
    "Albany, GA": "Albany, GA",
    "Utica": "Utica-Rome, NY",
    "Miami-Ft. Lauderdale": "Miami, FL",
    "Tallahassee-Thomasville": "Tallahassee-Thomasville, FL-GA",
    "Tri-Cities, TN-VA": "Johnson City-Kingsport, TN",
    "Albany-Schenectady-Troy": "Albany-Schenectady, NY",
    "Orlando-Daytona Bch-Melbrn": "Orlando, FL",
    "Columbus, OH": "Columbus, OH",
    "Rochester, NY": "Rochester, NY",
    "Tampa-St. Pete (Sarasota)": "Tampa-St. Petersburg, FL",
    "Traverse City-Cadillac": "Traverse City-Sault Ste. Marie, MI",
    "Springfield-Holyoke": "Springfield, MA",
    "Norfolk-Portsmth-Newpt Nws": "Norfolk-Virginia Beach, VA",
    "Greenville-N.Bern-Washngtn": "Greenville-Jacksonville, NC",
    "Columbia, SC": "Columbia, SC",
    "West Palm Beach-Ft. Pierce": "West Palm Beach-Port St. Lucie, FL",
    "Presque Isle": "Presque Isle-Caribou, ME",
    "Marquette": "Marquette-Escanaba, MI",
    "Wheeling-Steubenville": "Wheeling, WV",
    "Richmond-Petersburg": "Richmond, VA",
    "Bluefield-Beckley-Oak Hill": "Bluefield-Beckley, WV",
    "Grand Rapids-Kalmzoo-B.Crk": "Grand Rapids-Kalamazoo, MI",
    "Harrisburg-Lncstr-Leb-York": "Harrisburg-Lancaster, PA",
    "Greenvll-Spart-Ashevll-And": "Greenville-Spartanburg-Ashville, SC-NC",
    "Ft. Myers-Naples": "Ft. Myers-Cape Coral, FL",
    "Wilkes Barre-Scranton-Hztn": "Wilkes Barre-Scranton, PA",
    "Lafayette, IN": "Lafayette, IN",
    "Clarksburg-Weston": "Clarksburg-Fairmont, WV",
    "Joplin-Pittsburg": "Joplin, MO",
    "Columbia-Jefferson City": "Columbia, MO",
    "Rochestr-Mason City-Austin": "Rochester-Mason City, MN-IA",
    "Springfield, MO": "Springfield, MO",
    "Waco-Temple-Bryan": "Waco-Killeen, TX",
    "Wichita Falls & Lawton": "Wichita Falls-Lawton, TX-OK",
    "Monroe-El Dorado": "Monroe-El Dorado, LA-AR",
    "Paducah-Cape Girard-Harsbg": "Paducah-Cape Girardeau-Carbond, KY-MO-IL",
    "Harlingen-Wslco-Brnsvl-Mca": "Harlingen-Brownsville, TX",
    "Cedar Rapids-Wtrlo-IWC&Dub": "Cedar Rapids, IA",
    "Jackson, TN": "Jackson, TN",
    "Lafayette, LA": "Lafayette, LA",
    "Alexandria, LA": "Alexandria, LA",
    "Greenwood-Greenville": "Greenville, MS",
    "Champaign&Sprngfld-Decatur": "Springfield-Champaign, IL",
    "Evansville": "Evansville-Owensboro, IN-KY",
    "Sherman-Ada": "Sherman, TX",
    "Abilene-Sweetwater": "Abilene, TX",
    "Ft. Smith-Fay-Sprngdl-Rgrs": "Ft. Smith-Fayetteville, AR",
    "Columbus-Tupelo-West Point": "Columbus-Tupelo, MS",
    "Duluth-Superior": "Duluth, MN",
    "Wichita-Hutchinson Plus": "Wichita, KS",
    "Des Moines-Ames": "Des Moines, IA",
    "Davenport-R.Island-Moline": "Davenport, IA",
    "Mobile-Pensacola (Ft Walt)": "Mobile-Pensacola, AL-FL",
    "Minot-Bsmrck-Dcknsn(Wlstn)": "Bismarck, ND",
    "Huntsville-Decatur (Flor)": "Huntsville, AL",
    "Beaumont-Port Arthur": "Beaumont, TX",
    "Little Rock-Pine Bluff": "Little Rock, AR",
    "Montgomery-Selma": "Montgomery, AL",
    "Wausau-Rhinelander": "Wausau-Stevens Point, WI",
    "Hattiesburg-Laurel": "Hattiesburg, MS",
    "Quincy-Hannibal-Keokuk": "Quincy, IL",
    "Jackson, MS": "Jackson, MS",
    "Biloxi-Gulfport": "Gulfport, MS",
    "Denver": "Denver-Aurora, CO",
    "Colorado Springs-Pueblo": "Colorado Springs, CO",
    "Butte-Bozeman": "Butte-Bozeman-Silver Bow, MT",
    "Cheyenne-Scottsbluff": "Cheyenne, WY",
    "Casper-Riverton": "Casper, WY",
    "Yuma-El Centro": "Yuma-El Centro, AZ-CA",
    "Grand Junction-Montrose": "Grand Junction, CO",
    "Albuquerque-Santa Fe": "Albuquerque, NM",
    "Yakima-Pasco-Rchlnd-Knnwck": "Yakima-Kennewick, WA",
    "Medford-Klamath Falls": "Medford, OR",
    "Seattle-Tacoma": "Seattle, WA",
    "Portland, OR": "Portland, OR",
    "Bend, OR": "Bend, OR",
    "Santabarbra-Sanmar-Sanluob": "Santa Barbara-Santa Maria, CA",
    "Sacramnto-Stkton-Modesto": "Sacramento, CA",
    "Fresno-Visalia": "Fresno, CA",
}

# Validate overrides against actual ComScore market names before matching
print("Validating manual overrides against ComScore market names...")
actual_comscore_set = set(comscore_markets_df['comscore_market_full'])
override_warnings = []
for dma_name, comscore_full in MANUAL_OVERRIDES.items():
    if comscore_full not in actual_comscore_set:
        override_warnings.append(f"  WARNING: '{comscore_full}' (for DMA '{dma_name}') not found in ComScore data")
if override_warnings:
    print(f"Found {len(override_warnings)} override(s) that don't match ComScore market names exactly:")
    for w in override_warnings:
        print(w)
else:
    print("All overrides match ComScore market names.")

# Create mapping
print("\nMatching DMAs to ComScore markets...")
mapping_results = []

for idx, row in dma_df.iterrows():
    dma_code = row['DMA_code']
    dma_name = row['DMA_name']
    majority_state = row['majority_state']

    # Get all states for this DMA
    dma_states = dma_states_dict.get(dma_code, [])
    dma_states_str = ','.join(dma_states)

    # Apply manual override if available
    if dma_name in MANUAL_OVERRIDES:
        comscore_full = MANUAL_OVERRIDES[dma_name]
        market_name, state = parse_comscore_market(comscore_full)
        # Handle multi-state codes (e.g., "GA-SC", "KY-MO-IL")
        state_match = any(s in dma_states for s in state.split('-'))
        mapping_results.append({
            'DMA_code': dma_code,
            'DMA_name': dma_name,
            'DMA_majority_state': majority_state,
            'DMA_all_states': dma_states_str,
            'comscore_market_name': market_name,
            'comscore_state': state,
            'comscore_market_full': comscore_full,
            'state_match': 'Yes' if state_match else 'No',
            'match_score': 100,
            'match_method': 'manual',
            'needs_review': 'No'
        })
        continue

    # Fall back to automated fuzzy matching
    best_match_row, score, method, state_match = find_best_match(dma_name, dma_states, comscore_markets_df)

    if best_match_row is not None:
        mapping_results.append({
            'DMA_code': dma_code,
            'DMA_name': dma_name,
            'DMA_majority_state': majority_state,
            'DMA_all_states': dma_states_str,
            'comscore_market_name': best_match_row['comscore_market_name'],
            'comscore_state': best_match_row['comscore_state'],
            'comscore_market_full': best_match_row['comscore_market_full'],
            'state_match': 'Yes' if state_match else 'No',
            'match_score': score,
            'match_method': method,
            'needs_review': 'Yes' if score < 90 or not state_match else 'No'
        })
    else:
        mapping_results.append({
            'DMA_code': dma_code,
            'DMA_name': dma_name,
            'DMA_majority_state': majority_state,
            'DMA_all_states': dma_states_str,
            'comscore_market_name': None,
            'comscore_state': None,
            'comscore_market_full': None,
            'state_match': 'No',
            'match_score': score,
            'match_method': method,
            'needs_review': 'Yes'
        })

mapping_df = pd.DataFrame(mapping_results)

print(f"\nMatching complete!")
print(f"Total DMAs: {len(mapping_df)}")
print(f"Exact matches: {(mapping_df['match_method'] == 'exact').sum()}")
print(f"Partial matches: {(mapping_df['match_method'] == 'partial').sum()}")
print(f"Fuzzy matches: {(mapping_df['match_method'] == 'fuzzy').sum()}")
print(f"No matches: {(mapping_df['match_method'] == 'no_match').sum()}")
print(f"State matches: {(mapping_df['state_match'] == 'Yes').sum()}")
print(f"State mismatches: {(mapping_df['state_match'] == 'No').sum()}")
print(f"Needs review (score < 90, no state match, or no match): {(mapping_df['needs_review'] == 'Yes').sum()}")

print("\n" + "="*80)
print("Step 4: Review matches that need attention")
print("="*80)

needs_review = mapping_df[mapping_df['needs_review'] == 'Yes'].sort_values('match_score')
if len(needs_review) > 0:
    print(f"\nFound {len(needs_review)} matches that need review:")
    print(needs_review[['DMA_name', 'DMA_all_states', 'comscore_market_name', 'comscore_state', 'state_match', 'match_score', 'match_method']].to_string(index=False))
else:
    print("\nAll matches look good!")

print("\n" + "="*80)
print("Step 5: Identify unmatched ComScore markets")
print("="*80)

matched_comscore = set(mapping_df['comscore_market_full'].dropna())
all_comscore = set(comscore_markets_df['comscore_market_full'])
unmatched_comscore = all_comscore - matched_comscore

if len(unmatched_comscore) > 0:
    print(f"\nFound {len(unmatched_comscore)} ComScore markets without DMA matches:")
    for market in sorted(unmatched_comscore):
        print(f"  - {market}")
else:
    print("\nAll ComScore markets have been matched!")

print("\n" + "="*80)
print("Step 6: Save mapping")
print("="*80)

# Sort by DMA code
mapping_df = mapping_df.sort_values('DMA_code')

print(f"\nSaving full mapping to {output_file}...")
mapping_df.to_csv(output_file, index=False)
print("Done!")

# Save clean mapping for downstream merge (drop unmatched DMAs)
clean_output_file = os.path.join(output_dir, "DMA_comscore_mapping.csv")
clean_columns = ['DMA_code', 'DMA_name', 'DMA_majority_state', 'comscore_market_full']
clean_mapping = mapping_df[clean_columns].dropna(subset=['comscore_market_full'])
clean_mapping.to_csv(clean_output_file, index=False)
print(f"Saved clean mapping ({len(clean_mapping)} matched DMAs) to {clean_output_file}")

print("\n" + "="*80)
print("Summary Statistics")
print("="*80)
print(f"\nTotal DMAs: {len(dma_df)}")
print(f"Total ComScore markets: {len(comscore_markets_df)}")
print(f"Successfully matched: {(mapping_df['comscore_market_full'].notna()).sum()}")
print(f"Unmatched DMAs: {(mapping_df['comscore_market_full'].isna()).sum()}")
print(f"Unmatched ComScore markets: {len(unmatched_comscore)}")

print("\n" + "="*80)
print("Next Steps")
print("="*80)
print(f"""
1. Review the output file: {output_file}
2. Manually correct any matches with 'needs_review' = 'Yes'
3. For unmatched ComScore markets, determine if they should be mapped to existing DMAs
4. Once the mapping is finalized, it can be used to map ComScore data to DMAs and then to states
""")
