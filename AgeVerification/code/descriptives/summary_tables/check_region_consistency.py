#!/usr/bin/env python3
# Author: Hannah Lybbert
# Created: 2026-05-04
# Purpose: Check whether all persons attached to a given machine have the same
#          "region" value in the raw person_demos file, and whether that region
#          matches the machine's region in the raw machine_demos file.
#
#          Both files are from the same month (first available month).
#          Region is a person-level field in person_demos and a machine-level
#          field in machine_demos; ideally they should agree since region reflects
#          geography, not individual characteristics.
#
# Usage: python code/descriptives/summary_tables/check_region_consistency.py

import os
from glob import glob
import pandas as pd

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
raw_dir = os.path.join(project_root, "raw", "desktop_demographics")

SEP = "=" * 70

MACHINE_DEMO_COLS = [
    'machine_id', 'country', 'region', 'time_zone_bias', 'computer_location',
    'hoh_age', 'hh_income', 'children_present', 'hh_size', 'month_id'
]
PERSON_DEMO_COLS = [
    'person_id', 'machine_id', 'gender', 'age', 'children_present',
    'hh_income', 'hh_size', 'ethnicity_id', 'race_id', 'computer_location',
    'country', 'region', 'time_zone_bias', 'month_id'
]

# Use first available month
machine_files = sorted(
    glob(os.path.join(raw_dir, "US_comscore_machine_demos_*.txt")) +
    glob(os.path.join(raw_dir, "US_comscore_machine_demos_*.txt.gz"))
)
person_files = sorted(
    glob(os.path.join(raw_dir, "US_comscore_person_demos_*.txt")) +
    glob(os.path.join(raw_dir, "US_comscore_person_demos_*.txt.gz"))
)

if not machine_files or not person_files:
    print("ERROR: raw demo files not found in raw/desktop_demographics/")
    raise SystemExit(1)

machine_path = machine_files[0]
person_path  = person_files[0]
print(f"\n{SEP}")
print(f"Machine file: {os.path.basename(machine_path)}")
print(f"Person file:  {os.path.basename(person_path)}")
print(SEP)

# --- Load files ---
mach_comp = 'gzip' if machine_path.endswith('.gz') else None
pers_comp = 'gzip' if person_path.endswith('.gz')  else None

mach = pd.read_csv(
    machine_path, sep='\t', header=None, names=MACHINE_DEMO_COLS,
    compression=mach_comp, dtype=str, low_memory=False
)
mach['region'] = mach['region'].str.replace('"', '', regex=False)
print(f"\nMachine rows: {len(mach):,}  |  Unique machines: {mach['machine_id'].nunique():,}")

pers = pd.read_csv(
    person_path, sep='\t', header=None, names=PERSON_DEMO_COLS,
    compression=pers_comp, dtype=str, low_memory=False
)
pers['region'] = pers['region'].str.replace('"', '', regex=False)
print(f"Person rows:  {len(pers):,}  |  Unique persons: {pers['person_id'].nunique():,}")
print(f"              Unique machines in person file: {pers['machine_id'].nunique():,}")

# ==============================================================================
# CHECK 1: Within person_demos, do all persons on the same machine agree on region?
# ==============================================================================
print(f"\n{SEP}")
print("CHECK 1: Person-region consistency within machine (person_demos file)")
print(SEP)

pers_region = pers[['machine_id', 'person_id', 'region']].copy()

# Number of distinct regions per machine
region_per_mach = (
    pers_region.groupby('machine_id')['region']
    .nunique()
    .rename('n_distinct_regions')
    .reset_index()
)

n_machines_in_person = len(region_per_mach)
n_agree       = int((region_per_mach['n_distinct_regions'] == 1).sum())
n_disagree    = int((region_per_mach['n_distinct_regions'] >  1).sum())
n_null_only   = int(region_per_mach[
    region_per_mach['machine_id'].isin(
        pers_region.groupby('machine_id').filter(lambda x: x['region'].isna().all()).index
    )
].shape[0])

print(f"  Machines in person file:              {n_machines_in_person:,}")
print(f"  Machines where all persons agree:     {n_agree:,}  ({100*n_agree/n_machines_in_person:.1f}%)")
print(f"  Machines with >=2 distinct regions:   {n_disagree:,}  ({100*n_disagree/n_machines_in_person:.1f}%)")

if n_disagree > 0:
    print(f"\n  Distribution of n_distinct_regions for disagreeing machines:")
    print(region_per_mach[region_per_mach['n_distinct_regions'] > 1]
          ['n_distinct_regions'].value_counts().sort_index().to_string())

    # How many disagreements involve null vs. real mismatch?
    disagree_ids = region_per_mach.loc[region_per_mach['n_distinct_regions'] > 1, 'machine_id']
    disagree_pers = pers_region[pers_region['machine_id'].isin(disagree_ids)]
    n_has_null = int(disagree_pers.groupby('machine_id')['region'].apply(lambda x: x.isna().any()).sum())
    print(f"\n  Of those, machines where at least one person has null region: {n_has_null:,}")
    print(f"  Machines with disagreement but NO nulls (real mismatch):       {n_disagree - n_has_null:,}")

# ==============================================================================
# CHECK 2: Does person region match machine region?
# ==============================================================================
print(f"\n{SEP}")
print("CHECK 2: Person region vs. machine region (cross-file comparison)")
print(SEP)

# Use one representative region per machine from person file
# (first non-null, or null if all null)
person_region_rep = (
    pers.groupby('machine_id')['region']
    .apply(lambda x: x.dropna().iloc[0] if x.notna().any() else pd.NA)
    .rename('person_region')
    .reset_index()
)

mach_region = mach[['machine_id', 'region']].rename(columns={'region': 'machine_region'})

comparison = mach_region.merge(person_region_rep, on='machine_id', how='inner')
n_comp = len(comparison)
print(f"  Machines in both files: {n_comp:,}")

both_nonnull = comparison['machine_region'].notna() & comparison['person_region'].notna()
n_both = int(both_nonnull.sum())
match  = (comparison['machine_region'] == comparison['person_region']) & both_nonnull
n_match   = int(match.sum())
n_mismatch = n_both - n_match

print(f"  Both have non-null region:            {n_both:,}")
print(f"  Regions agree:                        {n_match:,}  ({100*n_match/n_both:.1f}% of non-null pairs)")
print(f"  Regions disagree:                     {n_mismatch:,}  ({100*n_mismatch/n_both:.1f}% of non-null pairs)")

if n_mismatch > 0:
    print(f"\n  Sample of mismatches (machine_region vs. person_region):")
    print(comparison[~match & both_nonnull][['machine_id', 'machine_region', 'person_region']]
          .head(20).to_string(index=False))

# ==============================================================================
# CHECK 3: How many persons appear on more than one machine?
# ==============================================================================
print(f"\n{SEP}")
print("CHECK 3: Persons with multiple machines (person_demos file)")
print(SEP)

machines_per_person = (
    pers.groupby('person_id')['machine_id']
    .nunique()
    .rename('n_machines')
    .reset_index()
)

n_persons_total = len(machines_per_person)
n_one    = int((machines_per_person['n_machines'] == 1).sum())
n_multi  = int((machines_per_person['n_machines'] >  1).sum())

print(f"  Total unique persons:               {n_persons_total:,}")
print(f"  Persons on exactly 1 machine:       {n_one:,}  ({100*n_one/n_persons_total:.1f}%)")
print(f"  Persons on 2+ machines:             {n_multi:,}  ({100*n_multi/n_persons_total:.1f}%)")

if n_multi > 0:
    print(f"\n  Distribution of n_machines for multi-machine persons:")
    print(machines_per_person[machines_per_person['n_machines'] > 1]
          ['n_machines'].value_counts().sort_index().to_string())

    # Do multi-machine persons always share the same region across their machines?
    multi_ids = machines_per_person.loc[machines_per_person['n_machines'] > 1, 'person_id']
    multi_pers = pers[pers['person_id'].isin(multi_ids)][['person_id', 'machine_id', 'region']]
    regions_per_person = (
        multi_pers.groupby('person_id')['region']
        .nunique()
        .rename('n_distinct_regions')
    )
    n_same_region  = int((regions_per_person == 1).sum())
    n_diff_region  = int((regions_per_person >  1).sum())
    print(f"\n  Of multi-machine persons:")
    print(f"    Same region across all machines:    {n_same_region:,}  ({100*n_same_region/n_multi:.1f}%)")
    print(f"    Different regions across machines:  {n_diff_region:,}  ({100*n_diff_region/n_multi:.1f}%)")

# ==============================================================================
# CHECK 4: How many persons have a null region vs. non-null?
# ==============================================================================
print(f"\n{SEP}")
print("CHECK 4: Null region stats in person_demos")
print(SEP)
n_null_region = int(pers['region'].isna().sum())
n_total_pers  = len(pers)
print(f"  Total person rows:      {n_total_pers:,}")
print(f"  Null region:            {n_null_region:,}  ({100*n_null_region/n_total_pers:.1f}%)")
print(f"  Non-null region:        {n_total_pers - n_null_region:,}")

print(f"\n  Top 20 region values in person_demos:")
print(pers['region'].value_counts(dropna=False).head(20).to_string())

print(f"\n{SEP}")
print("DONE")
print(SEP)
