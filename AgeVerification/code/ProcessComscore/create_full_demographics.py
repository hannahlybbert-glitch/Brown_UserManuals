# Author: Hannah Lybbert
# Created: 2026-02-26
# Updated: 2026-02-27
# Purpose: Build full-sample machine and person demographic reference files

"""
Create Full Demographics Files
Builds two demographic reference files spanning the full sample.

Outputs:
  data/ProcessComscore/full_demographics/machine_demographics.parquet
  data/ProcessComscore/full_demographics/person_demographics.parquet

machine_demographics.parquet — one row per unique machine_id ever in the sample:
  Columns: machine_id, have_demos, country, region, time_zone_bias, computer_location,
           hoh_age, hh_income, children_present, hh_size, state, majority_share
  have_demos: 1 if machine_id found in any Comscore machine demos file; 0 otherwise
  state/majority_share: taken from machine_to_state_lookup.parquet (already handles XX/ZZ)

person_demographics.parquet — one row per unique person_id ever in the sample:
  Columns: person_id, machine_id, have_demos, gender, age, children_present, hh_income,
           hh_size, ethnicity_id, race_id, computer_location, country, region, time_zone_bias
  have_demos: 1 if person_id found in person demo file for any month; 0 if session-only
  machine_id: taken from session data (authoritative), not from person demo file

Both universes are sourced from session files, guaranteeing every machine has at least
one linked person. Previously, 577K machines had person_count=0 because their panelists
were missing from the person demo files; this approach eliminates that problem.

Dependencies (must run first):
  - ProcessComscore/create_machine_state_lookup.py  (for all months)
  - Raw demographics files in raw/desktop_demographics/
  - Raw session files in raw/desktop_day_session/

Usage: python code/ProcessComscore/create_full_demographics.py
"""

import pandas as pd
import os
from glob import glob

# For cluster: comment out the os.chdir line
# os.chdir(r"C:\Users\hlybbert\OneDrive - The University of Chicago\Documents\AgeVerification")

project_root = os.getcwd()

print("=" * 80)
print("CREATE FULL DEMOGRAPHICS")
print("=" * 80)

# ----- OUTPUT DIR ----- #
output_dir = os.path.join(project_root, "data", "ProcessComscore", "full_demographics")
os.makedirs(output_dir, exist_ok=True)

# ----- COLUMN SCHEMAS (raw files have no header) ----- #
MACHINE_DEMO_COLS = [
    'machine_id', 'country', 'region', 'time_zone_bias', 'computer_location',
    'hoh_age', 'hh_income', 'children_present', 'hh_size', 'month_id'
]
PERSON_DEMO_COLS = [
    'person_id', 'machine_id', 'gender', 'age', 'children_present',
    'hh_income', 'hh_size', 'ethnicity_id', 'race_id', 'computer_location',
    'country', 'region', 'time_zone_bias', 'month_id'
]
SESSION_COLS = [
    'machine_id', 'person_id', 'session_id', 'time_id', 'first_ss2k',
    'pages', 'duration', 'pattern_id', 'ref_pattern_id', 'unknown_id'
]

# Columns to load from machine demo file (excludes month_id)
MACHINE_KEEP_COLS = [
    'machine_id', 'country', 'region', 'time_zone_bias', 'computer_location',
    'hoh_age', 'hh_income', 'children_present', 'hh_size'
]

# Columns to load from person demo file (excludes machine_id and month_id;
# machine_id comes from session data, which is the authoritative source)
PERSON_DEMO_READ_COLS = [
    'person_id', 'gender', 'age', 'children_present',
    'hh_income', 'hh_size', 'ethnicity_id', 'race_id',
    'computer_location', 'country', 'region', 'time_zone_bias'
]

# ==============================================================================
# MAIN LOOP: one pass per machine demo file (one per month)
# ==============================================================================
print("\n" + "=" * 80)
print("MAIN LOOP: Processing month-by-month from machine demo files")
print("=" * 80)

machine_demo_files = sorted(
    glob(os.path.join(project_root, "raw", "desktop_demographics", "US_comscore_machine_demos_*.txt")) +
    glob(os.path.join(project_root, "raw", "desktop_demographics", "US_comscore_machine_demos_*.txt.gz"))
)

if len(machine_demo_files) == 0:
    print("ERROR: No machine demographics files found in raw/desktop_demographics/")
    raise SystemExit(1)

print(f"Found {len(machine_demo_files)} machine demographics file(s)")

machine_chunks   = []
person_chunks    = []
months_processed = 0
months_skipped   = 0

for machine_demo_path in machine_demo_files:
    fname            = os.path.basename(machine_demo_path)
    demo_compression = 'gzip' if machine_demo_path.endswith('.gz') else None

    # ------------------------------------------------------------------
    # STEP 1: Read month_id from first row of machine demo file
    # ------------------------------------------------------------------
    temp = pd.read_csv(
        machine_demo_path,
        sep='\t',
        header=None,
        names=MACHINE_DEMO_COLS,
        usecols=['month_id'],
        nrows=1,
        compression=demo_compression
    )
    month_id = temp['month_id'].iloc[0]
    print(f"\n--- {fname}  (month_id={month_id}) ---")

    # ------------------------------------------------------------------
    # STEP 2: Read session file → (machine_id, person_id) only
    # Source for both machine and person universes this month.
    # ------------------------------------------------------------------
    session_gz  = os.path.join(project_root, "raw", "desktop_day_session",
                               f"comscore_desktop_day_session_{month_id}m.txt.gz")
    session_txt = os.path.join(project_root, "raw", "desktop_day_session",
                               f"comscore_desktop_day_session_{month_id}m.txt")

    if os.path.exists(session_gz):
        session_path        = session_gz
        session_compression = 'gzip'
    elif os.path.exists(session_txt):
        session_path        = session_txt
        session_compression = None
    else:
        print(f"  ERROR: Session file not found for month_id={month_id} — skipping month")
        months_skipped += 1
        continue

    session_pairs = pd.read_csv(
        session_path,
        sep='\t',
        header=None,
        names=SESSION_COLS,
        usecols=['machine_id', 'person_id'],
        compression=session_compression,
        dtype={'machine_id': str, 'person_id': str}
    )
    print(f"  Session rows: {len(session_pairs):,}")

    # ------------------------------------------------------------------
    # STEP 3: Build machine chunk
    # Universe: unique machine_ids from session.
    # Left-join machine demo file → demographic attributes.
    # Left-join machine_to_state_lookup → state, majority_share.
    # ------------------------------------------------------------------
    session_machines = session_pairs[['machine_id']].drop_duplicates()

    machine_demos = pd.read_csv(
        machine_demo_path,
        sep='\t',
        header=None,
        names=MACHINE_DEMO_COLS,
        usecols=MACHINE_KEEP_COLS,
        compression=demo_compression,
        dtype={'machine_id': str}
    )
    machine_demos['region'] = machine_demos['region'].str.replace('"', '', regex=False)

    machine_chunk = session_machines.merge(machine_demos, on='machine_id', how='left')

    lookup_path = os.path.join(
        project_root, "data", "ProcessComscore", "intermediate",
        str(month_id), "machine_to_state_lookup.parquet"
    )
    if os.path.exists(lookup_path):
        state_lookup  = pd.read_parquet(lookup_path, columns=['machine_id', 'state', 'majority_share'])
        machine_chunk = machine_chunk.merge(state_lookup, on='machine_id', how='left')
    else:
        print(f"  WARNING: machine_to_state_lookup.parquet not found for month_id={month_id}"
              f" — state/majority_share will be null")
        machine_chunk['state']          = pd.NA
        machine_chunk['majority_share'] = pd.NA

    machine_chunk['have_demos'] = machine_chunk['country'].notna().astype(int)
    print(f"  Machine chunk: {len(machine_chunk):,} rows  "
          f"(have_demos=1: {int(machine_chunk['have_demos'].sum()):,})")
    machine_chunks.append(machine_chunk)

    # ------------------------------------------------------------------
    # STEP 4: Build person chunk
    # Universe: unique person_ids from session (machine_id from session).
    # Left-join person demo file → demographic attributes.
    # have_demos=1 if person_id found in demo file, else 0.
    # ------------------------------------------------------------------
    # One row per person_id; if a person appears on multiple machines this
    # month (rare: 0.001% of persons), keep the first machine encountered.
    session_persons = (
        session_pairs[['person_id', 'machine_id']]
        .drop_duplicates(subset=['person_id'])
    )

    # Derive YYYYMM from machine demo filename to find matching person demo file
    yyyymm_str = (
        fname
        .replace('US_comscore_machine_demos_', '')
        .replace('.txt.gz', '')
        .replace('.txt', '')
    )

    person_demo_base = os.path.join(
        project_root, "raw", "desktop_demographics",
        f"US_comscore_person_demos_{yyyymm_str}.txt"
    )
    if os.path.exists(person_demo_base):
        person_demo_path  = person_demo_base
        person_compression = None
    elif os.path.exists(person_demo_base + '.gz'):
        person_demo_path  = person_demo_base + '.gz'
        person_compression = 'gzip'
    else:
        print(f"  WARNING: Person demo file not found for {yyyymm_str} — all persons have have_demos=0")
        session_persons = session_persons.copy()
        session_persons['have_demos'] = 0
        for col in ['gender', 'age', 'children_present', 'hh_income', 'hh_size',
                    'ethnicity_id', 'race_id', 'computer_location', 'country', 'region', 'time_zone_bias']:
            session_persons[col] = pd.NA
        person_chunks.append(session_persons)
        months_processed += 1
        continue

    person_demos = pd.read_csv(
        person_demo_path,
        sep='\t',
        header=None,
        names=PERSON_DEMO_COLS,
        usecols=PERSON_DEMO_READ_COLS,
        compression=person_compression,
        dtype={'person_id': str}
    )
    person_demos['region'] = person_demos['region'].str.replace('"', '', regex=False)

    person_chunk = session_persons.merge(person_demos, on='person_id', how='left')
    person_chunk['have_demos'] = person_chunk['country'].notna().astype(int)

    print(f"  Person chunk: {len(person_chunk):,} rows  "
          f"(have_demos=1: {int(person_chunk['have_demos'].sum()):,})")
    person_chunks.append(person_chunk)
    months_processed += 1

# ==============================================================================
# STEP 5: Assemble and save machine_demographics.parquet
# ==============================================================================
print("\n" + "=" * 80)
print("STEP 5: Assembling machine_demographics")
print("=" * 80)

if not machine_chunks:
    print("ERROR: No machine chunks were built. Check session and demo files.")
    raise SystemExit(1)

machine_demographics = (
    pd.concat(machine_chunks, ignore_index=True)
    # Sort so that rows with have_demos=1 (real demographics) come before have_demos=0
    # (session-only, no demographics registered yet). This ensures that a machine which
    # first appeared in sessions before its demographic profile was registered still gets
    # its correct state/region when it later appears in the demos file, rather than
    # being permanently assigned state=XX from the earlier no-demos record.
    # See: Comscore enrollment lag — machines start generating sessions immediately
    # upon software install, but demographic registration can lag by 1–2 months.
    .sort_values('have_demos', ascending=False)
    .drop_duplicates(subset=['machine_id'], keep='first')
    .reset_index(drop=True)
)

n_with    = int(machine_demographics['have_demos'].sum())
n_without = int((machine_demographics['have_demos'] == 0).sum())
print(f"  Total unique machines: {len(machine_demographics):,}")
print(f"  have_demos=1:          {n_with:,}")
print(f"  have_demos=0:          {n_without:,}")

machine_demographics = machine_demographics[[
    'machine_id', 'have_demos', 'country', 'region', 'time_zone_bias',
    'computer_location', 'hoh_age', 'hh_income', 'children_present', 'hh_size',
    'state', 'majority_share'
]]

out_machine = os.path.join(output_dir, "machine_demographics.parquet")
machine_demographics.to_parquet(out_machine, index=False, engine='pyarrow')
print(f"\nSaved: {out_machine}")
print(f"Shape: {machine_demographics.shape[0]:,} rows x {machine_demographics.shape[1]} columns")

# ==============================================================================
# STEP 6: Assemble and save person_demographics.parquet
# ==============================================================================
print("\n" + "=" * 80)
print("STEP 6: Assembling person_demographics")
print("=" * 80)

if not person_chunks:
    print("ERROR: No person chunks were built. Check session and demo files.")
    raise SystemExit(1)

person_demographics = (
    pd.concat(person_chunks, ignore_index=True)
    .drop_duplicates(subset=['person_id'], keep='first')
    .reset_index(drop=True)
)

n_p_with    = int(person_demographics['have_demos'].sum())
n_p_without = int((person_demographics['have_demos'] == 0).sum())
print(f"  Total unique persons: {len(person_demographics):,}")
print(f"  have_demos=1:         {n_p_with:,}")
print(f"  have_demos=0:         {n_p_without:,}")

person_demographics = person_demographics[[
    'person_id', 'machine_id', 'have_demos', 'gender', 'age', 'children_present',
    'hh_income', 'hh_size', 'ethnicity_id', 'race_id',
    'computer_location', 'country', 'region', 'time_zone_bias'
]]

out_person = os.path.join(output_dir, "person_demographics.parquet")
person_demographics.to_parquet(out_person, index=False, engine='pyarrow')
print(f"Saved: {out_person}")
print(f"Shape: {person_demographics.shape[0]:,} rows x {person_demographics.shape[1]} columns")

# ==============================================================================
# SUMMARY
# ==============================================================================
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Months processed:    {months_processed}")
print(f"Months skipped:      {months_skipped}")
print(f"\nmachine_demographics:")
print(f"  Rows:              {len(machine_demographics):,}")
print(f"  have_demos=1:      {n_with:,}")
print(f"  have_demos=0:      {n_without:,}")
print(f"  Columns:           {list(machine_demographics.columns)}")
print(f"\nperson_demographics:")
print(f"  Rows:              {len(person_demographics):,}")
print(f"  have_demos=1:      {n_p_with:,}")
print(f"  have_demos=0:      {n_p_without:,}")
print(f"  Columns:           {list(person_demographics.columns)}")
print(f"\nOutputs: {output_dir}")
print("=" * 80)
print("COMPLETE")
print("=" * 80)
