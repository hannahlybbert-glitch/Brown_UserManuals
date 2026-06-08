#!/usr/bin/env python3
# Author: Hannah Lybbert
# Created: 05/04/2026
# Purpose: Test the demographic files used in the final analysis pipeline
#          (same files read by prepare_combined.R) for unexpected gender==Unknown
#          values among machines that should have valid demographics.
#
#          Hypothesis: among machines with have_demos==1 and a valid state
#          (state not in EXCLUDE_STATES), gender should never be "Unknown"
#          because every person in the raw person_demos file has a gender value.
#          If Unknown appears for valid-state machines, something went wrong in
#          merge_full_demographics.py (likely person_count==0 machines that
#          somehow passed the have_demos filter, or have_demos mismatch between
#          machine and person files).
#
# Usage: python code/descriptives/summary_tables/check_analysis_sample_gender.py

import os
import pandas as pd

project_root  = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
demo_dir      = os.path.join(project_root, "data", "ProcessComscore", "full_demographics")
desk_path     = os.path.join(demo_dir, "full_machine_person_demos.parquet")
mobile_path   = os.path.join(project_root, "data", "ProcessComscore", "mobile_characteristics.csv")

EXCLUDE_STATES = {"DC", "XX", "ZZ"}
SEP = "=" * 70

# ==============================================================================
# DESKTOP: full_machine_person_demos.parquet
# ==============================================================================

print(f"\n{SEP}")
print("DESKTOP: full_machine_person_demos.parquet")
print(SEP)

desk = pd.read_parquet(desk_path)
print(f"  All rows:              {len(desk):,}")
print(f"  Columns: {list(desk.columns)}")

# What prepare_combined.R uses: have_demos == 1
desk_analysis = desk[desk['have_demos'] == 1].copy()
print(f"\n  have_demos == 1:       {len(desk_analysis):,}")

# State coverage
n_null_state = desk_analysis['state'].isna().sum()
print(f"  Null state:            {n_null_state:,}")
print(f"  Excluded states ({EXCLUDE_STATES}): "
      f"{desk_analysis['state'].isin(EXCLUDE_STATES).sum():,}")

# Valid-state machines (what enters the analysis after EXCLUDE_STATES filter)
desk_valid = desk_analysis[
    desk_analysis['state'].notna() &
    ~desk_analysis['state'].isin(EXCLUDE_STATES)
]
print(f"  Valid-state machines:  {len(desk_valid):,}")

# Gender distribution for valid-state machines
print(f"\n  Gender distribution (valid-state machines):")
g_counts = desk_valid['gender'].value_counts(dropna=False)
for label, n in g_counts.items():
    print(f"    {str(label):10s}: {n:>8,}  ({100 * n / len(desk_valid):.1f}%)")

# THE KEY CHECK: Unknown gender among valid-state machines
unknown_valid = desk_valid[desk_valid['gender'] == 'Unknown']
print(f"\n  *** gender==Unknown among valid-state machines: {len(unknown_valid):,} ***")

if len(unknown_valid) > 0:
    print(f"\n  person_count distribution for these Unknown machines:")
    print(unknown_valid['person_count'].value_counts(dropna=False).to_string())
    print(f"\n  have_demos distribution for these Unknown machines:")
    print(unknown_valid['have_demos'].value_counts(dropna=False).to_string())
    print(f"\n  State breakdown for Unknown + valid-state machines:")
    print(unknown_valid['state'].value_counts(dropna=False).to_string())

# ==============================================================================
# MOBILE: mobile_characteristics.csv
# ==============================================================================

print(f"\n{SEP}")
print("MOBILE: mobile_characteristics.csv")
print(SEP)

if not os.path.exists(mobile_path):
    print("  File not found — skipping.")
else:
    mob = pd.read_csv(mobile_path, dtype={'machine_id': str})
    print(f"  All rows:    {len(mob):,}")
    print(f"  Columns: {list(mob.columns)}")

    if 'gender' in mob.columns:
        print(f"\n  Gender distribution:")
        g_mob = mob['gender'].value_counts(dropna=False)
        for label, n in g_mob.items():
            print(f"    {str(label):10s}: {n:>8,}  ({100 * n / len(mob):.1f}%)")

        if 'state' in mob.columns:
            mob_valid = mob[mob['state'].notna() & ~mob['state'].isin(EXCLUDE_STATES)]
            unknown_mob = mob_valid[mob_valid['gender'] == 'Unknown']
            print(f"\n  *** gender==Unknown among valid-state mobile machines: {len(unknown_mob):,} ***")
            if len(unknown_mob) > 0:
                print(f"\n  State breakdown for Unknown mobile machines:")
                print(unknown_mob['state'].value_counts(dropna=False).to_string())
        else:
            print("\n  No 'state' column in mobile file.")
    else:
        print("\n  No 'gender' column in mobile file.")

print(f"\n{SEP}")
print("DONE")
print(SEP)
