# Author: Hannah Lybbert
# Created: 2026-02-26
# Purpose: Merge person demographics onto machine demographics to produce the
#          final machine-level demographic reference file for the Aggregation pipeline.
#
# Reads the two files produced by create_full_demographics.py and collapses
# person-level records to a single row per machine_id. The only person demographic
# that requires special handling is gender (see assign_gender below). Variables that
# are person-level only (race_id, ethnicity_id, age) are excluded.
#
# Inputs:
#   data/ProcessComscore/full_demographics/machine_demographics.parquet
#   data/ProcessComscore/full_demographics/person_demographics.parquet
#
# Output:
#   data/ProcessComscore/full_demographics/full_machine_person_demos.parquet
#   Columns: machine_id, have_demos, person_count, gender,
#            country, region, time_zone_bias, computer_location,
#            hoh_age, hh_income, children_present, hh_size,
#            state, majority_share
#
# Dependencies (must run first):
#   - ProcessComscore/create_full_demographics.py
#
# Usage: python code/ProcessComscore/merge_full_demographics.py

import pandas as pd
import os

# For cluster: comment out the os.chdir line
# os.chdir(r"C:\Users\hlybbert\OneDrive - The University of Chicago\Documents\AgeVerification")

project_root = os.getcwd()

print("=" * 80)
print("MERGE FULL DEMOGRAPHICS")
print("=" * 80)

# ----- PATHS ----- #
full_demo_dir = os.path.join(project_root, "data", "ProcessComscore", "full_demographics")
machine_path  = os.path.join(full_demo_dir, "machine_demographics.parquet")
person_path   = os.path.join(full_demo_dir, "person_demographics.parquet")

output_dir  = os.path.join(project_root, "data", "ProcessComscore", "full_demographics")
output_path = os.path.join(output_dir, "full_machine_person_demos.parquet")
os.makedirs(output_dir, exist_ok=True)

# ==============================================================================
# STEP 1: LOAD INPUTS
# ==============================================================================
print("\n" + "=" * 80)
print("STEP 1: Loading inputs")
print("=" * 80)

if not os.path.exists(machine_path):
    print(f"ERROR: {machine_path} not found.")
    print("Please run create_full_demographics.py first.")
    raise SystemExit(1)
if not os.path.exists(person_path):
    print(f"ERROR: {person_path} not found.")
    print("Please run create_full_demographics.py first.")
    raise SystemExit(1)

machine = pd.read_parquet(machine_path)
print(f"  machine_demographics: {len(machine):,} rows")

# Load person_id, machine_id, have_demos, and gender
person = pd.read_parquet(person_path, columns=['person_id', 'machine_id', 'have_demos', 'gender'])
print(f"  person_demographics:  {len(person):,} rows  ({person['machine_id'].nunique():,} unique machines)")

# ==============================================================================
# STEP 2: COMPUTE PER-MACHINE PERSON STATS
# ==============================================================================
print("\n" + "=" * 80)
print("STEP 2: Computing person_count and gender per machine")
print("=" * 80)

# Null out gender for persons with have_demos=0 — they have no reliable demographics
# and should not contribute to the machine-level gender label.
n_no_demos = int((person['have_demos'] == 0).sum())
if n_no_demos > 0:
    print(f"  Nulling gender for {n_no_demos:,} person rows with have_demos=0")
person.loc[person['have_demos'] == 0, 'gender'] = pd.NA

# Gender values are already string labels ('Male', 'Female') from person_demographics
person['gender_label'] = person['gender']

# person_count: number of unique person_ids per machine
person_count = (
    person.groupby('machine_id')['person_id']
    .nunique()
    .rename('person_count')
    .reset_index()
)

# For machines with at least one valid gender label, grab any one of them.
# Used for the person_count==1 case to return the actual 'Male'/'Female' label.
any_valid_gender = (
    person.loc[person['gender_label'].notna()]
    .groupby('machine_id')['gender_label']
    .first()
    .rename('any_valid_gender')
    .reset_index()
)

person_stats = person_count.merge(any_valid_gender, on='machine_id', how='left')

# Gender rule:
#   person_count == 1, valid gender   →  'Male' or 'Female'
#   person_count  > 1, valid gender   →  'Shared'  (can't attribute usage to one person)
#   no valid gender on any person     →  'Unknown'
def assign_gender(row):
    if pd.isna(row['any_valid_gender']):
        return 'Unknown'
    if row['person_count'] == 1:
        return row['any_valid_gender']
    return 'Shared'

person_stats['gender'] = person_stats.apply(assign_gender, axis=1)
person_stats = person_stats.drop(columns=['any_valid_gender'])

n_with_persons = len(person_stats)
print(f"  Machines with at least one person: {n_with_persons:,}")
print(f"\n  Gender distribution (machines with persons):")
for label, count in person_stats['gender'].value_counts().items():
    print(f"    {label:10s}: {count:>8,}  ({count / n_with_persons * 100:.1f}%)")

# ==============================================================================
# STEP 3: MERGE ONTO MACHINE_DEMOGRAPHICS
# ==============================================================================
print("\n" + "=" * 80)
print("STEP 3: Merging person stats onto machine demographics")
print("=" * 80)

merged = machine.merge(person_stats, on='machine_id', how='left')

n_no_persons = int(merged['person_count'].isna().sum())
print(f"  Machines with no persons in person file: {n_no_persons:,}")

merged['person_count'] = merged['person_count'].fillna(0).astype(int)
merged['gender']       = merged['gender'].fillna('Unknown')

# ==============================================================================
# STEP 4: FINALIZE AND SAVE
# ==============================================================================
print("\n" + "=" * 80)
print("STEP 4: Saving")
print("=" * 80)

merged = merged[[
    'machine_id', 'have_demos', 'person_count', 'gender',
    'country', 'region', 'time_zone_bias', 'computer_location',
    'hoh_age', 'hh_income', 'children_present', 'hh_size',
    'state', 'majority_share',
]]

merged.to_parquet(output_path, index=False, engine='pyarrow')
print(f"  Saved: {output_path}")
print(f"  Shape: {merged.shape[0]:,} rows x {merged.shape[1]} columns")

# ==============================================================================
# SUMMARY
# ==============================================================================
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"  Total machines:       {len(merged):,}")
print(f"  have_demos=1:         {int(merged['have_demos'].sum()):,}")
print(f"  have_demos=0:         {int((merged['have_demos'] == 0).sum()):,}")
print(f"  person_count=0:       {int((merged['person_count'] == 0).sum()):,}")
print(f"\n  Gender distribution (full file):")
for label, count in merged['gender'].value_counts().items():
    print(f"    {label:10s}: {count:>8,}  ({count / len(merged) * 100:.1f}%)")
q = merged['person_count']
print(f"\n  person_count distribution:")
print(f"    p25={q.quantile(.25):.1f}  p50={q.quantile(.50):.1f}  "
      f"p75={q.quantile(.75):.1f}  p90={q.quantile(.90):.1f}  "
      f"p99={q.quantile(.99):.1f}  max={q.max():.1f}")
print(f"\n  Output: {output_path}")
print("=" * 80)
print("COMPLETE")
print("=" * 80)
