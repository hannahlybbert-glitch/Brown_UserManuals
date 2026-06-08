# Author: Emily Davis
# Created: 2026-03-24
# Purpose: Build full-sample mobile machine demographic reference file
#          (parallel to create_full_demographics.py + merge_full_demographics.py
#          for desktop, but a single script since mobile device = one person)

"""
Create Full Mobile Demographics File
Builds a machine-level demographic reference file spanning the full sample.

Output:
  data/ProcessComscore/full_demographics/full_mobile_demos.parquet

Columns: machine_id, have_demos, platform, age, gender, hh_income, hh_size,
         children_present, region, race, hispanic, state, majority_share

have_demos: 1 if machine_id found in any mobile demographics file; 0 otherwise

The machine universe is sourced from the mobile session files (not the demo
files), so every machine with at least one browsing session is represented —
including machines that never appeared in a demographics file (have_demos=0).
This mirrors the approach in create_full_demographics.py for desktop.

For machines observed in multiple months, we keep the first row where
have_demos=1 (i.e., demographics were available). If a machine only ever
appears without demographics, we keep its first session-only record.

Dependencies (must run first):
  - ProcessComscore/create_mobile_state_lookup.py  (for all months)
  - Raw mobile demographics files in raw/mobile_demographics/
  - Raw mobile session files in raw/mobile_day_session/

Usage: python code/ProcessComscore/create_full_mobile_demographics.py
"""

import pandas as pd
import os
from glob import glob

project_root = os.getcwd()

print("=" * 80)
print("CREATE FULL MOBILE DEMOGRAPHICS")
print("=" * 80)

# ----- OUTPUT DIR ----- #
output_dir = os.path.join(project_root, "data", "ProcessComscore", "full_demographics")
os.makedirs(output_dir, exist_ok=True)

# ----- COLUMN SCHEMAS (raw files have no header) ----- #
MOBILE_SESSION_COLS = [
    'month_id', 'session_id', 'machine_id', 'platform', 'access_method_name',
    'time_id', 'calendar_day', 'event_time', 'ss2k', 'pages', 'duration', 'pattern_id'
]

MOBILE_DEMO_COLS = [
    'month_id', 'platform', 'machine_id', 'age', 'gender',
    'hh_income', 'hh_size', 'children_present', 'region', 'race', 'hispanic'
]

MOBILE_DEMO_KEEP_COLS = [
    'machine_id', 'platform', 'age', 'gender',
    'hh_income', 'hh_size', 'children_present', 'region', 'race', 'hispanic'
]

# ==============================================================================
# MAIN LOOP: one pass per mobile demographics file (one per month)
# ==============================================================================
print("\n" + "=" * 80)
print("MAIN LOOP: Processing month-by-month from mobile demo files")
print("=" * 80)

mobile_demo_files = sorted(
    glob(os.path.join(project_root, "raw", "mobile_demographics", "US_comscore_mobile_demos_*.txt")) +
    glob(os.path.join(project_root, "raw", "mobile_demographics", "US_comscore_mobile_demos_*.txt.gz"))
)

if len(mobile_demo_files) == 0:
    print("ERROR: No mobile demographics files found in raw/mobile_demographics/")
    raise SystemExit(1)

print(f"Found {len(mobile_demo_files)} mobile demographics file(s)")

machine_chunks   = []
months_processed = 0
months_skipped   = 0

for demo_path in mobile_demo_files:
    fname            = os.path.basename(demo_path)
    demo_compression = 'gzip' if demo_path.endswith('.gz') else None

    # ------------------------------------------------------------------
    # STEP 1: Read month_id from first row of mobile demo file
    # ------------------------------------------------------------------
    temp = pd.read_csv(
        demo_path,
        sep='\t',
        header=None,
        names=MOBILE_DEMO_COLS,
        usecols=['month_id'],
        nrows=1,
        compression=demo_compression
    )
    month_id = temp['month_id'].iloc[0]
    print(f"\n--- {fname}  (month_id={month_id}) ---")

    # ------------------------------------------------------------------
    # STEP 2: Read mobile session file → unique machine_ids
    # This is the universe: every machine observed in sessions this month.
    # ------------------------------------------------------------------
    session_gz  = os.path.join(project_root, "raw", "mobile_day_session",
                               f"comscore_mobile_day_session_{month_id}m.txt.gz")
    session_txt = os.path.join(project_root, "raw", "mobile_day_session",
                               f"comscore_mobile_day_session_{month_id}m.txt")

    if os.path.exists(session_gz):
        session_path        = session_gz
        session_compression = 'gzip'
    elif os.path.exists(session_txt):
        session_path        = session_txt
        session_compression = None
    else:
        print(f"  ERROR: Mobile session file not found for month_id={month_id} — skipping month")
        months_skipped += 1
        continue

    session_machines = pd.read_csv(
        session_path,
        sep='\t',
        header=None,
        names=MOBILE_SESSION_COLS,
        usecols=['machine_id'],
        compression=session_compression,
        dtype={'machine_id': str}
    ).drop_duplicates()
    print(f"  Unique machines in sessions: {len(session_machines):,}")

    # ------------------------------------------------------------------
    # STEP 3: Read mobile demo file and left-join onto session machines
    # ------------------------------------------------------------------
    mobile_demos = pd.read_csv(
        demo_path,
        sep='\t',
        header=None,
        names=MOBILE_DEMO_COLS,
        usecols=MOBILE_DEMO_KEEP_COLS,
        compression=demo_compression,
        dtype={'machine_id': str}
    )
    # Clean quotes from string columns
    string_cols = ['platform', 'gender', 'hh_income', 'hh_size',
                   'children_present', 'region', 'race', 'hispanic']
    for col in string_cols:
        mobile_demos[col] = mobile_demos[col].astype(str).str.strip('"').str.strip("'")

    # Keep first demo record per machine (in case of duplicates within a month)
    mobile_demos = mobile_demos.drop_duplicates(subset=['machine_id'], keep='first')

    machine_chunk = session_machines.merge(mobile_demos, on='machine_id', how='left')

    # ------------------------------------------------------------------
    # STEP 4: Left-join mobile state lookup → state, majority_share
    # ------------------------------------------------------------------
    lookup_path = os.path.join(
        project_root, "data", "ProcessComscore", "intermediate",
        str(month_id), "mobile_to_state_lookup.parquet"
    )
    if os.path.exists(lookup_path):
        state_lookup  = pd.read_parquet(lookup_path, columns=['machine_id', 'state', 'majority_share'])
        state_lookup['machine_id'] = state_lookup['machine_id'].astype(str)
        machine_chunk = machine_chunk.merge(state_lookup, on='machine_id', how='left')
    else:
        print(f"  WARNING: mobile_to_state_lookup.parquet not found for month_id={month_id}"
              f" — state/majority_share will be null")
        machine_chunk['state']          = pd.NA
        machine_chunk['majority_share'] = pd.NA

    # ------------------------------------------------------------------
    # STEP 5: Flag machines with demographics
    # have_demos=1 if the machine matched in the demo file (age is non-null)
    # ------------------------------------------------------------------
    machine_chunk['have_demos'] = machine_chunk['age'].notna().astype(int)

    n_with    = int(machine_chunk['have_demos'].sum())
    n_without = len(machine_chunk) - n_with
    print(f"  Machine chunk: {len(machine_chunk):,} rows  "
          f"(have_demos=1: {n_with:,}  have_demos=0: {n_without:,})")

    machine_chunks.append(machine_chunk)
    months_processed += 1

# ==============================================================================
# ASSEMBLE AND SAVE
# ==============================================================================
print("\n" + "=" * 80)
print("ASSEMBLING full_mobile_demos")
print("=" * 80)

if not machine_chunks:
    print("ERROR: No machine chunks were built. Check session and demo files.")
    raise SystemExit(1)

full_mobile_demos = (
    pd.concat(machine_chunks, ignore_index=True)
    # Sort so have_demos=1 rows come first — ensures a machine that first appeared
    # in sessions before its demo was registered still gets its demographics
    # when it later appears in the demo file (same enrollment-lag logic as desktop).
    .sort_values('have_demos', ascending=False)
    .drop_duplicates(subset=['machine_id'], keep='first')
    .reset_index(drop=True)
)

n_with    = int(full_mobile_demos['have_demos'].sum())
n_without = int((full_mobile_demos['have_demos'] == 0).sum())
print(f"  Total unique machines: {len(full_mobile_demos):,}")
print(f"  have_demos=1:          {n_with:,}")
print(f"  have_demos=0:          {n_without:,}")

full_mobile_demos = full_mobile_demos[[
    'machine_id', 'have_demos', 'platform', 'age', 'gender',
    'hh_income', 'hh_size', 'children_present', 'region', 'race', 'hispanic',
    'state', 'majority_share'
]]

output_path = os.path.join(output_dir, "full_mobile_demos.parquet")
full_mobile_demos.to_parquet(output_path, index=False, engine='pyarrow')
print(f"\nSaved: {output_path}")
print(f"Shape: {full_mobile_demos.shape[0]:,} rows x {full_mobile_demos.shape[1]} columns")

# ==============================================================================
# SUMMARY
# ==============================================================================
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Months processed:    {months_processed}")
print(f"Months skipped:      {months_skipped}")
print(f"\nfull_mobile_demos:")
print(f"  Rows:              {len(full_mobile_demos):,}")
print(f"  have_demos=1:      {n_with:,}")
print(f"  have_demos=0:      {n_without:,}")
print(f"  Columns:           {list(full_mobile_demos.columns)}")
print(f"\nCharacteristic coverage (have_demos=1 machines):")
demos_only = full_mobile_demos[full_mobile_demos['have_demos'] == 1]
for col in ['platform', 'age', 'gender', 'hh_income', 'hh_size',
            'children_present', 'region', 'race', 'hispanic', 'state']:
    coverage = demos_only[col].notna().sum()
    pct = coverage / len(demos_only) * 100
    print(f"  {col}: {coverage:,} ({pct:.1f}%)")
print(f"\nOutput: {output_path}")
print("=" * 80)
print("COMPLETE")
print("=" * 80)
