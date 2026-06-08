# Author: Hannah Lybbert
# Created: 2026-03-03
# Purpose: Check whether VPN-related sites appear in the Comscore traffic_category_map lookup files.
#          Searches for (1) any "VPN" keyword in web_name/category/subcategory and
#          (2) specific known VPN provider domains.
#
# NOTE on Norton/us.norton.com:
#   In Comscore, "us.norton.com" appears as "US Norton.com" (Channel, web_id=15598989),
#   which is a child of "NORTON.COM" (Media Title), which is itself a child of
#   "Symantec" (Property, web_id=202297, parent_id=1).
#   Because create_crosswalk_file.py traverses to the ROOT (parent_id=1),
#   all Norton visits (including us.norton.com) appear as top_web_name="Symantec"
#   in the merged_session_files. Search for "symantec" — not "norton.com" — in merged data.

'''
Input:  raw/Lookups/traffic_category_map/comscore_category_map_*.txt[.gz]
Output: printed summary to console
'''

import pandas as pd
import os
import glob
import sys

# Fix Windows console encoding issues with non-ASCII characters in web names
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


# ----- CONFIG ----- #

COLUMNS = [
    'month_id', 'pattern_id', 'web_id', 'web_name', 'level_name', 'level_id',
    'parent_id', 'subcategory', 'category', 'Magazine', 'Streaming_Video', 'Blog',
    'Streaming_Audio', 'Cable_Broadcast_TV', 'Radio', 'Newspaper'
]

# Domains to search for in web_name.
# norton.com is replaced with symantec: in the Comscore hierarchy, all Norton
# traffic (including us.norton.com) rolls up to the root Property "Symantec".
# norton.com itself is a child Media Title under Symantec, so it never appears
# as a top_web_name in merged_session_files.
VPN_DOMAINS = [
    'nordvpn.com',
    'surfshark.com',
    'ipvanish.com',
    'totalvpn.com',
    'protonvpn.com',
    'symantec',           # root Property for all Norton/us.norton.com traffic
    'expressvpn.com',
    'bitdefender.com',
    'cyberghostvpn.com',
    'privateinternetaccess.com',
    'mullvad.net',
    'hotshield.com',
    'purevpn.com',
    'tunnelbear.com',
    'hide.me',
    'privadovpn.com',
    'ivpn.net',
    'airvpn.org',
    'windscribe.com',
    'perfect-privacy.com',
]

# Text columns to search for "VPN" keyword
TEXT_COLS = ['web_name', 'category', 'subcategory']

# web_names to exclude from the VPN keyword search (confirmed non-VPN sites)
KEYWORD_EXCLUSIONS = {
    'VPNEWS.RU',   # Russian news site; "VPN" in name is coincidental
}

N_EXAMPLES = 5  # number of example rows to print per search type per file


# ----- HELPERS ----- #

def load_file(path):
    compression = 'gzip' if path.endswith('.gz') else None
    df = pd.read_csv(
        path, sep='\t', header=None, names=COLUMNS,
        dtype=str, compression=compression, low_memory=False
    )
    return df


def search_vpn_keyword(df):
    """Return rows where any text column contains 'vpn' (case-insensitive),
    excluding known non-VPN sites."""
    mask = pd.Series(False, index=df.index)
    for col in TEXT_COLS:
        mask |= df[col].str.contains('vpn', case=False, na=False)
    hits = df[mask]
    # Apply exclusions (case-insensitive match on web_name)
    exclusion_mask = hits['web_name'].str.upper().isin(
        {e.upper() for e in KEYWORD_EXCLUSIONS}
    )
    excluded = hits[exclusion_mask]
    hits = hits[~exclusion_mask]
    return hits, excluded


def search_domain(df, domain):
    """Return rows where web_name contains the given domain (case-insensitive)."""
    mask = df['web_name'].str.contains(domain, case=False, na=False)
    return df[mask]


def print_examples(hits, n=N_EXAMPLES):
    display_cols = ['pattern_id', 'web_id', 'parent_id', 'web_name', 'level_name', 'category', 'subcategory']
    sample = hits[display_cols].head(n)
    print(sample.to_string(index=False))


# ----- MAIN ----- #

base_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', '..')
)
map_dir = os.path.join(base_dir, 'raw', 'Lookups', 'traffic_category_map')

files = sorted(
    glob.glob(os.path.join(map_dir, 'comscore_category_map_*.txt')) +
    glob.glob(os.path.join(map_dir, 'comscore_category_map_*.txt.gz'))
)

if not files:
    print(f"ERROR: No category map files found in {map_dir}")
    raise SystemExit(1)

print("=" * 70)
print("VPN SITE CHECK — Comscore traffic_category_map files")
print("=" * 70)
print(f"Files to scan: {len(files)}")
for f in files:
    print(f"  {os.path.basename(f)}")
print()
print("NOTE: norton.com/us.norton.com traffic rolls up to root Property")
print("      'Symantec' in merged_session_files. Searching 'symantec' here.")
print(f"NOTE: Excluding from VPN keyword hits: {sorted(KEYWORD_EXCLUSIONS)}")
print()

# Collect counts for aggregate summary
summary = {}

for path in files:
    fname = os.path.basename(path)
    print("-" * 70)
    print(f"FILE: {fname}")
    print("-" * 70)

    df = load_file(path)
    print(f"  Total rows loaded: {len(df):,}\n")

    file_counts = {}

    # 1. VPN keyword search (with exclusions)
    kw_hits, kw_excluded = search_vpn_keyword(df)
    file_counts['vpn_keyword_hits'] = len(kw_hits)
    file_counts['vpn_keyword_excluded'] = len(kw_excluded)
    print(f"  [VPN keyword in web_name/category/subcategory]")
    print(f"  Hits: {len(kw_hits):,}  |  Excluded (non-VPN): {len(kw_excluded):,}")
    if not kw_hits.empty:
        print(f"  Examples (first {N_EXAMPLES}):")
        print_examples(kw_hits)
    if not kw_excluded.empty:
        print(f"  Excluded examples:")
        print_examples(kw_excluded)
    print()

    # 2. Per-domain search
    print(f"  [Known VPN domain hits in web_name]")
    any_domain_hits = False
    for domain in VPN_DOMAINS:
        dom_hits = search_domain(df, domain)
        file_counts[domain] = len(dom_hits)
        if len(dom_hits) > 0:
            any_domain_hits = True
            print(f"\n  {domain}: {len(dom_hits)} hit(s)")
            print_examples(dom_hits)
    if not any_domain_hits:
        print("  No hits for any of the specified domains.")
    print()

    summary[fname] = file_counts

# ----- AGGREGATE SUMMARY TABLE ----- #
print("=" * 70)
print("AGGREGATE SUMMARY")
print("=" * 70)

rows = []
for fname, counts in summary.items():
    row = {'file': fname}
    row.update(counts)
    rows.append(row)

summary_df = pd.DataFrame(rows).set_index('file')

print("\nVPN keyword hits per file (after exclusions):")
print(summary_df[['vpn_keyword_hits', 'vpn_keyword_excluded']].to_string())

print("\nSpecific VPN domain hits per file:")
domain_cols = [d for d in VPN_DOMAINS if d in summary_df.columns]
print(summary_df[domain_cols].to_string())

print("\n" + "=" * 70)
print("DONE")
print("=" * 70)
