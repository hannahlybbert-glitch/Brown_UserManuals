# Author: Hannah Lybbert
# Created: 2026-02-26
# Purpose: Check whether demographic variables are machine-level or person-level
#
# For machines with multiple persons, tests whether key variables vary across
# persons sharing the same machine. Also cross-checks person file values against
# machine file values to detect encoding differences.
#
# Usage: python code/descriptives/check_demo_variable_levels.py YYYYMM
# Example: python code/descriptives/check_demo_variable_levels.py 202201

import pandas as pd
import os
import sys

# For cluster: comment out the os.chdir line
# os.chdir(r"C:\Users\hlybbert\OneDrive - The University of Chicago\Documents\AgeVerification")

if len(sys.argv) != 2:
    print("Usage: python check_demo_variable_levels.py YYYYMM")
    sys.exit(1)

yyyymm = sys.argv[1]

MACHINE_COLS = ['machine_id', 'country', 'region', 'time_zone_bias', 'computer_location',
                'hoh_age', 'hh_income', 'children_present', 'hh_size', 'month_id']
PERSON_COLS  = ['person_id', 'machine_id', 'gender', 'age', 'children_present',
                'hh_income', 'hh_size', 'ethnicity_id', 'race_id', 'computer_location',
                'country', 'region', 'time_zone_bias', 'month_id']

def load_file(base_path, col_names):
    for path, compression in [(base_path, None), (base_path + '.gz', 'gzip')]:
        if os.path.exists(path):
            return pd.read_csv(path, sep='\t', header=None, names=col_names,
                               compression=compression, dtype={'machine_id': str, 'person_id': str})
    print(f"ERROR: File not found: {base_path}")
    sys.exit(1)

machine = load_file(f'raw/desktop_demographics/US_comscore_machine_demos_{yyyymm}.txt', MACHINE_COLS)
person  = load_file(f'raw/desktop_demographics/US_comscore_person_demos_{yyyymm}.txt',  PERSON_COLS)

print("=" * 70)
print(f"DEMOGRAPHIC VARIABLE LEVEL CHECK — {yyyymm}")
print("=" * 70)
print(f"\nMachine file rows: {len(machine):,}  |  Person file rows: {len(person):,}")

# Machines with multiple people
multi = person.groupby('machine_id').filter(lambda x: len(x) > 1)
n_machines = multi['machine_id'].nunique()
print(f"Machines with multiple people: {n_machines:,}\n")

# ------------------------------------------------------------------
# SECTION 1: Variation within machine (person file only)
# ------------------------------------------------------------------
print("=" * 70)
print("SECTION 1: Within-machine variation (person file)")
print("Does the variable differ across persons sharing a machine?")
print("=" * 70)

person_vars = ['region', 'children_present', 'hh_size', 'hh_income', 'computer_location', 'age']
for var in person_vars:
    varies = multi.groupby('machine_id')[var].nunique()
    n_vary = (varies > 1).sum()
    pct = n_vary / n_machines * 100
    level = "PERSON-level" if n_vary > 0 else "machine-level"
    print(f"  {var:<22} varies in {n_vary:>6,} / {n_machines:,} machines ({pct:.1f}%)  [{level}]")

# ------------------------------------------------------------------
# SECTION 2: Cross-file comparison (person value vs machine value)
# ------------------------------------------------------------------
print()
print("=" * 70)
print("SECTION 2: Cross-file value comparison")
print("Do person file and machine file agree on shared variables?")
print("(100% mismatch often indicates encoding difference, not disagreement)")
print("=" * 70)

merged = multi.merge(
    machine[['machine_id', 'hoh_age', 'hh_income', 'children_present', 'hh_size', 'computer_location', 'region']],
    on='machine_id', suffixes=('_person', '_machine')
)

cross_vars = [
    ('region',            'region'),
    ('children_present',  'children_present'),
    ('hh_size',           'hh_size'),
    ('hh_income',         'hh_income'),
    ('computer_location', 'computer_location'),
]
for pvar, mvar in cross_vars:
    pcol, mcol = pvar + '_person', mvar + '_machine'
    mismatch = (merged[pcol] != merged[mcol]).sum()
    pct = mismatch / len(merged) * 100
    note = " (encoding difference)" if pct == 100.0 else ""
    print(f"  {pvar:<22} mismatch in {mismatch:>8,} / {len(merged):,} rows ({pct:.1f}%){note}")

# ------------------------------------------------------------------
# SECTION 3: Unique value inspection for mismatched variables
# ------------------------------------------------------------------
print()
print("=" * 70)
print("SECTION 3: Unique values for variables with encoding differences")
print("=" * 70)

for var in ['hh_size', 'hh_income']:
    print(f"\n  {var} — machine file:")
    print(f"    {sorted(machine[var].dropna().unique())}")
    print(f"  {var} — person file:")
    print(f"    {sorted(person[var].dropna().unique())}")

print()
print("=" * 70)
print("COMPLETE")
print("=" * 70)
