#!/usr/bin/env python3
# Author: Hannah Lybbert
# Created: 05/04/2026
# Purpose: Diagnostic — reads one raw US_comscore_person_demos_* file and
#          prints unique gender values, unique region values, and how many
#          null-gender person rows have a non-null state (state joined from
#          full_machine_person_demos.parquet).
#
# Usage: python code/descriptives/summary_tables/check_demo_state_coverage.py

import os
from glob import glob
import pandas as pd

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
demo_dir = os.path.join(project_root, "data", "ProcessComscore", "full_demographics")
raw_dir  = os.path.join(project_root, "raw", "desktop_demographics")

machine_demos_path = os.path.join(demo_dir, "full_machine_person_demos.parquet")

SEP = "=" * 70

PERSON_DEMO_COLS = [
    'person_id', 'machine_id', 'gender', 'age', 'children_present',
    'hh_income', 'hh_size', 'ethnicity_id', 'race_id', 'computer_location',
    'country', 'region', 'time_zone_bias', 'month_id'
]

# ==============================================================================
# RAW PERSON DEMOS FILE
# ==============================================================================

person_raw_files = sorted(
    glob(os.path.join(raw_dir, "US_comscore_person_demos_*.txt")) +
    glob(os.path.join(raw_dir, "US_comscore_person_demos_*.txt.gz"))
)

if not person_raw_files:
    print("ERROR: No US_comscore_person_demos_* files found in raw/desktop_demographics/")
    raise SystemExit(1)

print(f"\n{SEP}")
print(f"RAW FILE: {os.path.basename(person_raw_files[0])}  (person demos)")
print(SEP)

praw = pd.read_csv(
    person_raw_files[0], sep='\t', header=None, names=PERSON_DEMO_COLS,
    compression='gzip' if person_raw_files[0].endswith('.gz') else None,
    dtype=str, low_memory=False
)
print(f"  Rows: {len(praw):,}  |  Columns: {list(praw.columns)}")

print(f"\n  Unique gender values:")
print(praw['gender'].value_counts(dropna=False).to_string())

print(f"\n  Unique region values ({praw['region'].nunique()} total):")
print(praw['region'].value_counts(dropna=False).to_string())

# Null gender rows with a non-null state
# (state joined from full_machine_person_demos.parquet)
mach = pd.read_parquet(machine_demos_path, columns=['machine_id', 'state'])
state_lookup = mach.drop_duplicates('machine_id')
praw_w_state = praw.merge(state_lookup, on='machine_id', how='left')

null_gender      = praw_w_state['gender'].isna()
nonnull_state    = praw_w_state['state'].notna()
n_null_g_total   = int(null_gender.sum())
n_null_g_valid_s = int((null_gender & nonnull_state).sum())

print(f"\n  Null gender rows:                       {n_null_g_total:,}")
if n_null_g_total > 0:
    print(f"  Null gender + non-null state:           {n_null_g_valid_s:,}"
          f"  ({100 * n_null_g_valid_s / n_null_g_total:.1f}% of null-gender rows)")
else:
    print("  (no null gender rows)")

print(f"\n{SEP}")
print("DONE")
print(SEP)

# ==============================================================================
# PRIOR ANALYSIS (commented out)
# ==============================================================================

# print(f"\n{SEP}")
# print("FILE: full_machine_person_demos.parquet")
# print(SEP)
# mach_full = pd.read_parquet(machine_demos_path)
# print(f"  Rows:    {len(mach_full):,}")
# print(f"  Columns: {list(mach_full.columns)}")
# n_null_state = mach_full['state'].isna().sum()
# print(f"\n  Null state:     {n_null_state:,}  ({100 * n_null_state / len(mach_full):.1f}%)")
# print(f"  Non-null state: {(~mach_full['state'].isna()).sum():,}")
# print("\n  Machines by state:")
# state_counts = mach_full['state'].value_counts(dropna=False).rename('n_machines').reset_index()
# state_counts.columns = ['state', 'n_machines']
# state_counts['pct'] = (100 * state_counts['n_machines'] / len(mach_full)).round(1)
# print(state_counts.to_string(index=False))
# unknown = mach_full[mach_full['gender'] == 'Unknown']
# print(f"\n  Gender == 'Unknown': {len(unknown):,}  ({100*len(unknown)/len(mach_full):.1f}%)")
# print(unknown['state'].value_counts(dropna=False).to_string())

# print(f"\n{SEP}")
# print("FILE: person_demographics.parquet")
# print(SEP)
# person_demos_path = os.path.join(demo_dir, "person_demographics.parquet")
# person = pd.read_parquet(person_demos_path)
# print(f"  Rows: {len(person):,}  ({person['machine_id'].nunique():,} unique machines)")
# print(f"  Columns: {list(person.columns)}")
# if 'state' not in person.columns:
#     print("  No 'state' column — joining from full_machine_person_demos.parquet")
#     person_w_state = person.merge(state_lookup, on='machine_id', how='left')
#     print(f"  Null state after join: {person_w_state['state'].isna().sum():,}")
#     print(person_w_state['state'].value_counts(dropna=False).to_string())
