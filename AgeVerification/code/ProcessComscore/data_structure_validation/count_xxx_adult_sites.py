# Author: Hannah Lybbert
# Created: 2026-05-06
# Purpose: Count unique web_id and web_name values with category="XXX Adult"
#          across all Comscore category map files. Reads each file in chunks to
#          avoid loading the full file into memory. Tracks a running set of seen
#          sites so each file only contributes new entries to the master list.
#
# Input:  raw/Lookups/traffic_category_map/comscore_category_map_*.txt[.gz]
# Output: printed summary to console (redirect to log via SLURM or shell)

import pandas as pd
import os
import glob
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ----- CONFIG ----- #

COLUMNS = [
    'month_id', 'pattern_id', 'web_id', 'web_name', 'level_name', 'level_id',
    'parent_id', 'subcategory', 'category', 'Magazine', 'Streaming_Video', 'Blog',
    'Streaming_Audio', 'Cable_Broadcast_TV', 'Radio', 'Newspaper'
]

TARGET_CATEGORY = 'XXX Adult'
CHUNKSIZE = 50_000   # rows per chunk — keeps peak memory low


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
print("XXX ADULT SITE COUNT — Comscore traffic_category_map files")
print("=" * 70)
print(f"Files to scan: {len(files)}")
for f in files:
    print(f"  {os.path.basename(f)}")
print()

# Running set of all XXX Adult sites seen so far across files.
# Storing (web_id, web_name) pairs so the sample output at the end is useful.
seen_sites = {}   # web_id -> web_name (first time we see the site)

per_file = []

for path in files:
    fname = os.path.basename(path)
    print("-" * 70)
    print(f"FILE: {fname}")
    print("-" * 70)

    compression = 'gzip' if path.endswith('.gz') else None

    file_ids   = set()   # web_ids found in this file
    file_names = set()   # web_names found in this file
    new_ids    = set()   # web_ids not seen in any prior file
    total_rows = 0

    reader = pd.read_csv(
        path, sep='\t', header=None, names=COLUMNS,
        dtype=str, compression=compression, low_memory=False,
        chunksize=CHUNKSIZE
    )

    for chunk in reader:
        total_rows += len(chunk)
        xxx = chunk[chunk['subcategory'].str.strip() == TARGET_CATEGORY]
        if xxx.empty:
            continue
        for _, row in xxx[['web_id', 'web_name']].dropna(subset=['web_id']).iterrows():
            wid  = row['web_id']
            wnam = row['web_name']
            file_ids.add(wid)
            file_names.add(wnam)
            if wid not in seen_sites:
                seen_sites[wid] = wnam
                new_ids.add(wid)

    print(f"  Total rows scanned:       {total_rows:,}")
    print(f"  Unique web_id  (this file):    {len(file_ids):,}")
    print(f"  Unique web_name (this file):   {len(file_names):,}")
    print(f"  New web_id not seen before:    {len(new_ids):,}")
    print(f"  Running total unique web_id:   {len(seen_sites):,}")
    print()

    per_file.append({
        'file':              fname,
        'unique_web_id':     len(file_ids),
        'unique_web_name':   len(file_names),
        'new_web_id':        len(new_ids),
        'running_total':     len(seen_sites),
    })

# ----- COMBINED SUMMARY ----- #
print("=" * 70)
print("COMBINED SUMMARY ACROSS ALL FILES")
print("=" * 70)

summary_df = pd.DataFrame(per_file).set_index('file')
print(summary_df.to_string())

print()
print(f"Total unique web_id   with category='XXX Adult': {len(seen_sites):,}")
print(f"Total unique web_name with category='XXX Adult': {len(set(seen_sites.values())):,}")

print()
print("Sample of unique XXX Adult sites (up to 20):")
sample = list(seen_sites.items())[:20]
for wid, wnam in sample:
    print(f"  web_id={wid:>10}  web_name={wnam}")

print()
print("=" * 70)
print("DONE")
print("=" * 70)
