# Author: Hannah Lybbert
# Created: 01/21/2026
# Purpose: Creating website characteristics file

'''
Input: raw/Lookups/traffic_category_map/comscore_category_map_[YYYYMM].txt
Output: data/ProcessComscore/intermediate/[month_id]/web_characteristics.parquet (columns: top_web_id, top_web_name, category,
subcategory)

  How to use in command line: python create_web_characteristics.py YYYYMM
        Ex: python create_web_characteristics.py 202201

'''


# Imports
import pandas as pd
import numpy as np
import os
import sys

# Local testing only - comment out when running from terminal
# os.chdir(r"C:\Users\hlybbert\OneDrive - The University of Chicago\Documents\AgeVerification")

# ----- LOAD DATA ----- #
# Get YYYYMM from command line argument
if len(sys.argv) != 2:
    print("Usage: python create_web_characteristics.py YYYYMM")
    print("Example: python create_web_characteristics.py 202201")
    sys.exit(1)

yyyymm = sys.argv[1]

# Construct input path using YYYYMM (try .gz first, then .txt)
input_path_gz = f'raw/Lookups/traffic_category_map/comscore_category_map_{yyyymm}.txt.gz'
input_path_txt = f'raw/Lookups/traffic_category_map/comscore_category_map_{yyyymm}.txt'

if os.path.exists(input_path_gz):
    input_path = input_path_gz
    compression = 'gzip'
elif os.path.exists(input_path_txt):
    input_path = input_path_txt
    compression = None
else:
    print(f"ERROR: Category map file not found for {yyyymm}")
    print(f"  Tried: {input_path_gz}")
    print(f"  Tried: {input_path_txt}")
    sys.exit(1)

# Reconstruct dataframe from txt file
df = pd.read_csv(input_path, sep='\t', header=None,
                names=['month_id', 'pattern_id', 'web_id', 'web_name', 'level_name', 'level_id',
            'parent_id', 'subcategory', 'category', 'Magazine', 'Streaming_Video', 'Blog',
            'Streaming_Audio', 'Cable_Broadcast_TV', 'Radio', 'Newspaper'],
                compression=compression)

# Extract month_id from the data (should be consistent across all rows)
month_id = df['month_id'].iloc[0]

# Construct output path using month_id
output_dir = f"data/ProcessComscore/intermediate/{month_id}"
output_path = f"{output_dir}/web_characteristics.parquet"

# Create output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)


# ----- WEB CHARACTERISTICS, BUILD FILE ----- #
# Filter to root webpages only (where parent_id == 1), this will grab only the parent (root) webpages
root_pages = df[df['parent_id'] == 1].copy()

# Create website characteristics [website_info] dataframe
website_info = root_pages[['web_id', 'web_name', 'category', 'subcategory']].drop_duplicates(subset=['web_id'])

# Rename columns to indicate these are top-level websites
website_info = website_info.rename(columns={
    'web_id': 'top_web_id',
    'web_name': 'top_web_name'
})

# Ensure consistent string type for merge key
website_info['top_web_id'] = website_info['top_web_id'].astype(str)

# ----- VPN SITE INDICATOR ----- #
# 1a. Explicit whitelists for two VPN tiers.
#
# VPN_CLEAN_WHITELIST: top 3 pure VPN providers → coarse category 'VPNclean'
VPN_CLEAN_WHITELIST = {
    'NORDVPN.COM',
    'EXPRESSVPN.COM',
    'SURFSHARK.COM',
}

# VPN_WHITELIST: all other confirmed VPN root Properties → coarse category 'allVPN'
# Note: Symantec and BITDEFENDER.COM are broad antivirus companies — VPN sessions
# are overcounted; tracked separately in diagnostics.
# Note: CYBERGHOSTVPN.COM Sites excluded — 104 sessions/visitor anomaly indicates
# automated traffic, not real browsing; falls through to all_other_sites.
VPN_WHITELIST = {
    'TOTALVPN.COM',
    'PRIVATEINTERNETACCESS.COM',
    'PUREVPN.COM',
    'TunnelBear Sites',
    'HIDE.ME',
    'WINDSCRIBE.COM',
    'PERFECT-PRIVACY.COM',
    'Symantec',
    'Gen Digital Inc. (Formally Symantec - NortonLifeLock)',
    'BITDEFENDER.COM',
}

# 1b. Final vpn_clean_site flag (top 3 pure VPN providers only)
# Note: Dynamic keyword detection was removed after confirming across all 36 months of
# Comscore data that the intended targets (ProtonVPN, Mullvad, Hotshield, PrivadoVPN,
# IVPN, AirVPN) do not appear in Comscore at all. The only site the regex ever caught
# was KODIVPN.CO (18 visitors) — an unintended false positive from the 'ivpn' substring.
# Removal has no effect on coverage for real VPN providers.
website_info['vpn_clean_site'] = website_info['top_web_name'].isin(VPN_CLEAN_WHITELIST)
print(f"VPN clean site flag: {website_info['vpn_clean_site'].sum():,} websites flagged as vpn_clean_site=True.")

# 1c. Final vpn_site flag (all whitelisted VPN sites; includes VPN_CLEAN_WHITELIST)
# Priority in assign_coarse_category() ensures vpn_clean_site takes precedence over vpn_site.
website_info['vpn_site'] = (
    website_info['top_web_name'].isin(VPN_CLEAN_WHITELIST) |
    website_info['top_web_name'].isin(VPN_WHITELIST)
)
print(f"VPN site flag: {website_info['vpn_site'].sum():,} websites flagged as vpn_site=True.")

# ----- GITHUB PORN DOMAIN INDICATOR ----- #
# Load github porn domains list and add indicator column
github_porn_path = "data/external/github_porn_domains.txt"

# Second-level TLDs for proper base domain extraction
second_level_tlds = {'co.uk', 'org.uk', 'com.br', 'com.au', 'co.nz', 'co.jp',
                     'co.kr', 'com.mx', 'com.ar', 'com.co', 'co.za'}

def extract_base_domain(domain: str) -> str:
    """Extract base domain (e.g., xxx.tumblr.com -> tumblr.com)."""
    domain = domain.lower().strip()
    if domain.startswith('www.'):
        domain = domain[4:]
    parts = domain.split('.')
    if len(parts) <= 2:
        return domain
    if len(parts) >= 3 and '.'.join(parts[-2:]) in second_level_tlds:
        return '.'.join(parts[-3:])
    return '.'.join(parts[-2:])

if os.path.exists(github_porn_path):
    with open(github_porn_path) as f:
        raw_domains = [line.strip().lower() for line in f if line.strip()]
    github_base_domains = set(extract_base_domain(d) for d in raw_domains)
    print(f"Loaded {len(github_base_domains):,} unique base domains from GitHub porn domains list.")

    # Create indicator: check if top_web_name (normalized) is in github base domains
    # Note: Only extract base domain from github list, not from comscore names (matches validate_adult_classification.py logic)
    website_info['github_porn_domain'] = website_info['top_web_name'].str.lower().str.strip().isin(github_base_domains)
    print(f"Matched {website_info['github_porn_domain'].sum():,} websites to GitHub porn domains list.")
else:
    print(f"WARNING: GitHub porn domains file not found at {github_porn_path}")
    print("         github_porn_domain column will be set to False for all rows.")
    website_info['github_porn_domain'] = False

# ----- OUTPUT - WEB CHARACTERISTICS FILE ----- #
website_info.to_parquet(output_path, index=False)

print(f"Processing month: {yyyymm} (month_id: {month_id})")
print(f"Website characteristics file created with {len(website_info)} unique websites.")
print(f"Output saved to: {output_path}")


