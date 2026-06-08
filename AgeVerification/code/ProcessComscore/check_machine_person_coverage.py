#!/usr/bin/env python3
# Author: Hannah Lybbert
# Created: 2026-05-04
# Purpose: For each month in the raw desktop demographics files, report how many
#          unique machines appear in the machine_demos file, how many of those
#          machines also appear in the person_demos file, and the gap.
#
#          This confirms whether gender==Unknown in full_machine_person_demos.parquet
#          is explained purely by machines that have no person records (vs. a
#          processing bug).
#
# Usage: python code/ProcessComscore/check_machine_person_coverage.py
#        (or via sbatch — no cluster-specific dependencies)

import os
from glob import glob
import pandas as pd

project_root = os.getcwd()
raw_dir      = os.path.join(project_root, "raw", "desktop_demographics")

SEP = "=" * 80

MACHINE_DEMO_COLS = [
    'machine_id', 'country', 'region', 'time_zone_bias', 'computer_location',
    'hoh_age', 'hh_income', 'children_present', 'hh_size', 'month_id'
]
PERSON_DEMO_COLS = [
    'person_id', 'machine_id', 'gender', 'age', 'children_present',
    'hh_income', 'hh_size', 'ethnicity_id', 'race_id', 'computer_location',
    'country', 'region', 'time_zone_bias', 'month_id'
]

print(SEP)
print("MACHINE vs. PERSON COVERAGE CHECK (all months)")
print(SEP)

machine_files = sorted(
    glob(os.path.join(raw_dir, "US_comscore_machine_demos_*.txt")) +
    glob(os.path.join(raw_dir, "US_comscore_machine_demos_*.txt.gz"))
)

if not machine_files:
    print("ERROR: No machine demo files found.")
    raise SystemExit(1)

print(f"Found {len(machine_files)} machine demo file(s)\n")

rows = []

# Accumulate unique machine_ids across all months for cross-month dedup
all_machine_ids = set()
all_person_machine_ids = set()

for mpath in machine_files:
    fname      = os.path.basename(mpath)
    mcomp      = 'gzip' if mpath.endswith('.gz') else None
    yyyymm_str = (fname
                  .replace('US_comscore_machine_demos_', '')
                  .replace('.txt.gz', '')
                  .replace('.txt', ''))

    # Read machine file — only need machine_id
    mach = pd.read_csv(
        mpath, sep='\t', header=None, names=MACHINE_DEMO_COLS,
        usecols=['machine_id'], compression=mcomp, dtype={'machine_id': str},
        low_memory=False
    )
    mach_ids = set(mach['machine_id'].dropna().unique())
    n_mach   = len(mach_ids)
    all_machine_ids.update(mach_ids)

    # Find matching person file
    pbase = os.path.join(raw_dir, f"US_comscore_person_demos_{yyyymm_str}.txt")
    if os.path.exists(pbase):
        ppath = pbase
        pcomp = None
    elif os.path.exists(pbase + '.gz'):
        ppath = pbase + '.gz'
        pcomp = 'gzip'
    else:
        print(f"  {yyyymm_str}: machine={n_mach:,}  person=MISSING")
        rows.append({'month': yyyymm_str, 'n_machines': n_mach,
                     'n_machines_in_person': None, 'n_gap': None,
                     'pct_no_person': None, 'person_file': False})
        continue

    pers = pd.read_csv(
        ppath, sep='\t', header=None, names=PERSON_DEMO_COLS,
        usecols=['machine_id'], compression=pcomp, dtype={'machine_id': str},
        low_memory=False
    )
    pers_ids    = set(pers['machine_id'].dropna().unique())
    n_pers_mach = len(pers_ids)
    all_person_machine_ids.update(pers_ids)

    n_gap       = n_mach - n_pers_mach
    pct_no_pers = 100.0 * n_gap / n_mach if n_mach > 0 else float('nan')

    print(f"  {yyyymm_str}: machines={n_mach:>7,}  "
          f"in_person_file={n_pers_mach:>7,}  "
          f"gap={n_gap:>7,}  ({pct_no_pers:.1f}% no person record)")

    rows.append({
        'month':                yyyymm_str,
        'n_machines':           n_mach,
        'n_machines_in_person': n_pers_mach,
        'n_gap':                n_gap,
        'pct_no_person':        round(pct_no_pers, 1),
        'person_file':          True,
    })

# ==============================================================================
# SUMMARY
# ==============================================================================
print(f"\n{SEP}")
print("SUMMARY")
print(SEP)

summary = pd.DataFrame(rows)
valid   = summary[summary['person_file'] == True]

if len(valid) > 0:
    total_mach      = int(valid['n_machines'].sum())
    total_in_person = int(valid['n_machines_in_person'].sum())
    total_gap       = int(valid['n_gap'].sum())

    print(f"  Months with both files:        {len(valid)}")
    print(f"  Months missing person file:    {int((summary['person_file'] == False).sum())}")
    print(f"\n  Across all months (row-sums, not deduped across months):")
    print(f"    Total machine-month rows:    {total_mach:,}")
    print(f"    In person file:              {total_in_person:,}  ({100*total_in_person/total_mach:.1f}%)")
    print(f"    Gap (no person record):      {total_gap:,}  ({100*total_gap/total_mach:.1f}%)")

    print(f"\n  Per-month gap range:")
    print(f"    Min gap %:  {valid['pct_no_person'].min():.1f}%  ({valid.loc[valid['pct_no_person'].idxmin(), 'month']})")
    print(f"    Max gap %:  {valid['pct_no_person'].max():.1f}%  ({valid.loc[valid['pct_no_person'].idxmax(), 'month']})")
    print(f"    Mean gap %: {valid['pct_no_person'].mean():.1f}%")

# Cross-month deduplication
n_uniq_mach       = len(all_machine_ids)
n_uniq_with_pers  = len(all_machine_ids & all_person_machine_ids)
n_uniq_never_pers = len(all_machine_ids - all_person_machine_ids)
pct_never          = 100.0 * n_uniq_never_pers / n_uniq_mach if n_uniq_mach > 0 else float('nan')

print(f"\n  Across all months (unique machines, deduped):")
print(f"    Total unique machines:                    {n_uniq_mach:,}")
print(f"    Seen in a person file at least once:      {n_uniq_with_pers:,}  ({100*n_uniq_with_pers/n_uniq_mach:.1f}%)")
print(f"    Never seen in any person file:            {n_uniq_never_pers:,}  ({pct_never:.1f}%)")

print(f"\n{SEP}")
print("DONE")
print(SEP)
