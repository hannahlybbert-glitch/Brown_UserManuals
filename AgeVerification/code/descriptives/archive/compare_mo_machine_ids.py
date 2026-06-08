# Author: Hannah Lybbert
# Created: 02/11/2026
# Purpose: Compare machine_ids in demographics file vs session file for a given month

"""
Diagnostic: Compare Machine IDs in Demographics vs Sessions

Checks if all machines with sessions have corresponding demographics data.
This diagnoses whether missing states are caused by machines having sessions
but no demographics for that month.

Usage: python compare_mo_machine_ids.py YYYYMM
Example: python compare_mo_machine_ids.py 202201
"""

import pandas as pd
import os
import sys

# For cluster: comment out the os.chdir line
os.chdir(r"C:\Users\hlybbert\OneDrive - The University of Chicago\Documents\AgeVerification")

# Get YYYYMM from command line argument
if len(sys.argv) != 2:
    print("Usage: python compare_mo_machine_ids.py YYYYMM")
    print("Example: python compare_mo_machine_ids.py 202201")
    sys.exit(1)

yyyymm = sys.argv[1]

print("="*80)
print(f"MACHINE ID COMPARISON: {yyyymm}")
print("="*80)

# ==============================================================================
# 1. LOAD DEMOGRAPHICS FILE
# ==============================================================================
print("\n" + "="*80)
print("1. LOADING DEMOGRAPHICS FILE")
print("="*80)

# Check for both .txt (local) and .txt.gz (cluster)
demographics_path_base = f'raw/desktop_demographics/US_comscore_machine_demos_{yyyymm}.txt'
if os.path.exists(demographics_path_base):
    demographics_path = demographics_path_base
    demo_compression = None
elif os.path.exists(demographics_path_base + '.gz'):
    demographics_path = demographics_path_base + '.gz'
    demo_compression = 'gzip'
else:
    print(f"ERROR: Desktop demographics file not found for {yyyymm}")
    print(f"  Tried: {demographics_path_base} and {demographics_path_base}.gz")
    sys.exit(1)

print(f"Reading: {demographics_path}")

# Load only machine_id and month_id columns
desktop_columns = ['machine_id', 'country', 'region', 'time_zone_bias', 'computer_location',
                   'hoh_age', 'hh_income', 'children_present', 'hh_size', 'month_id']

demographics = pd.read_csv(
    demographics_path,
    sep='\t',
    header=None,
    names=desktop_columns,
    usecols=['machine_id', 'month_id'],
    compression=demo_compression,
    dtype={'machine_id': str}
)

month_id = demographics['month_id'].iloc[0]
demo_machines = set(demographics['machine_id'].unique())

print(f"Month ID: {month_id}")
print(f"Total rows in demographics: {len(demographics):,}")
print(f"Unique machine_ids: {len(demo_machines):,}")

# ==============================================================================
# 2. LOAD SESSION FILE
# ==============================================================================
print("\n" + "="*80)
print("2. LOADING SESSION FILE")
print("="*80)

# Try both compressed and uncompressed session files
session_file_gz = f"raw/desktop_day_session/comscore_desktop_day_session_{month_id}m.txt.gz"
session_file_txt = f"raw/desktop_day_session/comscore_desktop_day_session_{month_id}m.txt"

if os.path.exists(session_file_gz):
    session_file = session_file_gz
    session_compression = 'gzip'
elif os.path.exists(session_file_txt):
    session_file = session_file_txt
    session_compression = None
else:
    print(f"ERROR: Session file not found for month_id {month_id}")
    print(f"  Tried: {session_file_gz}")
    print(f"  Tried: {session_file_txt}")
    sys.exit(1)

print(f"Reading: {session_file}")
print("(This may take a moment for large files...)")

# Load only machine_id column
sessions = pd.read_csv(
    session_file,
    sep='\t',
    header=None,
    names=['machine_id', 'person_id', 'session_id', 'time_id', 'first_ss2k',
           'pages', 'duration', 'pattern_id', 'ref_pattern_id', 'unknown_id'],
    usecols=['machine_id'],
    compression=session_compression,
    dtype={'machine_id': str}
)

session_machines = set(sessions['machine_id'].unique())

print(f"Total sessions: {len(sessions):,}")
print(f"Unique machine_ids: {len(session_machines):,}")

# ==============================================================================
# 3. COMPARE MACHINE IDs
# ==============================================================================
print("\n" + "="*80)
print("3. COMPARISON ANALYSIS")
print("="*80)

# Machines in both
in_both = demo_machines & session_machines
print(f"\nMachines in BOTH files: {len(in_both):,}")

# Machines only in demographics (have demos but no sessions)
only_in_demo = demo_machines - session_machines
print(f"\nMachines ONLY in demographics: {len(only_in_demo):,}")
if len(only_in_demo) > 0:
    pct = (len(only_in_demo) / len(demo_machines)) * 100
    print(f"  ({pct:.2f}% of demographics machines)")
    print("  These machines have demographics but no sessions for this month")

# Machines only in sessions (have sessions but no demos) - THIS IS THE PROBLEM!
only_in_sessions = session_machines - demo_machines
print(f"\nMachines ONLY in sessions: {len(only_in_sessions):,}")
if len(only_in_sessions) > 0:
    pct = (len(only_in_sessions) / len(session_machines)) * 100
    print(f"  ({pct:.2f}% of session machines)")
    print("  *** THIS IS THE ISSUE! ***")
    print("  These machines have sessions but NO demographics for this month")
    print("  They will have missing states in the merged data!")

    # Count sessions from these machines
    sessions_from_missing = sessions[sessions['machine_id'].isin(only_in_sessions)]
    print(f"\n  Sessions from these machines: {len(sessions_from_missing):,}")
    sessions_pct = (len(sessions_from_missing) / len(sessions)) * 100
    print(f"  ({sessions_pct:.2f}% of all sessions)")

# ==============================================================================
# 4. COVERAGE STATISTICS
# ==============================================================================
print("\n" + "="*80)
print("4. COVERAGE STATISTICS")
print("="*80)

coverage_rate = (len(in_both) / len(session_machines)) * 100
print(f"\nDemographics coverage of session machines: {coverage_rate:.2f}%")
print(f"  ({len(in_both):,} out of {len(session_machines):,} machines)")

if len(only_in_sessions) > 0:
    print(f"\nMissing coverage: {100 - coverage_rate:.2f}%")
    print(f"  ({len(only_in_sessions):,} machines with sessions but no demographics)")

# ==============================================================================
# 5. SAMPLE OF PROBLEMATIC MACHINES
# ==============================================================================
if len(only_in_sessions) > 0:
    print("\n" + "="*80)
    print("5. SAMPLE OF MACHINES WITH SESSIONS BUT NO DEMOGRAPHICS")
    print("="*80)

    # Get sample sessions from problematic machines
    sample_size = min(20, len(only_in_sessions))
    sample_machines = list(only_in_sessions)[:sample_size]

    print(f"\nShowing first {sample_size} problematic machine_ids:")
    for i, machine_id in enumerate(sample_machines, 1):
        session_count = (sessions['machine_id'] == machine_id).sum()
        print(f"  {i:2d}. {machine_id}: {session_count:,} sessions")

# ==============================================================================
# 6. RECOMMENDATIONS
# ==============================================================================
print("\n" + "="*80)
print("6. RECOMMENDATIONS")
print("="*80)

if len(only_in_sessions) == 0:
    print("\n✓ All machines with sessions have demographics!")
    print("  The missing state issue must be elsewhere in the pipeline.")
else:
    print(f"\n✗ {len(only_in_sessions):,} machines have sessions but NO demographics")
    print(f"  This accounts for {sessions_pct:.2f}% of all sessions")
    print("\nRECOMMENDED FIX:")
    print("  1. Modify create_machine_state_lookup.py to:")
    print("     - Load unique machine_ids from SESSION file (not demographics)")
    print("     - Look up demographics/region for those machines")
    print("     - Use most recent available demographics if current month missing")
    print("\n  2. OR: Accept that ~16% of sessions will have missing states")
    print("     - Filter these out during aggregation")
    print("     - Document this as a data limitation")

print("\n" + "="*80)
print("END OF COMPARISON")
print("="*80)
