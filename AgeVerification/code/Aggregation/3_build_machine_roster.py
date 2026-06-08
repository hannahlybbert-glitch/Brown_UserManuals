# Author: Hannah Lybbert
# Created: 02/23/2026
# Purpose: Build machine roster files for machine-level panel assembly

"""
Build Machine Roster (Script 3 of 5)
Scans all 36 intermediate session files (reading only the columns needed) and outputs:

  1. machine_week_presence.parquet  — one row per (machine_id, week_of_sample) observed;
                                      ground truth for the NULL vs. zero distinction in script 5
  2. boundary_weeks.csv            — weeks that span two calendar months (appear in 2+ files)

Run once before scripts 4 and 5. No arguments required.

Note: machine_demographics.parquet and person_demographics.parquet are produced by
      code/ProcessComscore/create_full_demographics.py — run that separately.

Usage: python 3_build_machine_roster.py
"""

import pandas as pd
import os
import sys
from glob import glob
from collections import defaultdict

# For cluster: comment out the os.chdir line
# os.chdir(r"C:\Users\hlybbert\OneDrive - The University of Chicago\Documents\AgeVerification")

# Get the project root directory
project_root = os.getcwd()

# --test flag: use intermediate_test/ and machine_panel_test/ instead of real data
TEST_MODE = "--test" in sys.argv

print("=" * 80)
print("BUILD MACHINE ROSTER" + (" [TEST MODE]" if TEST_MODE else ""))
print("=" * 80)

# ----- FILE PATHS ----- #
intermediate_dir = os.path.join(
    project_root, "data", "Aggregation",
    "intermediate_test" if TEST_MODE else "intermediate"
)
output_dir = os.path.join(
    project_root, "data", "Aggregation",
    "machine_panel_test" if TEST_MODE else "machine_panel"
)
os.makedirs(output_dir, exist_ok=True)

# ----- FIND ALL INTERMEDIATE FILES ----- #
print(f"\n[SETUP] Finding intermediate session files...")
intermediate_files = sorted(
    glob(os.path.join(intermediate_dir, "*", "intermediate_sessions_*.parquet"))
)

if len(intermediate_files) == 0:
    print(f"ERROR: No intermediate files found in {intermediate_dir}")
    print("Please run scripts 1 and 2 first.")
    exit(1)

print(f"  Found {len(intermediate_files)} intermediate files:")
for f in intermediate_files:
    print(f"    - {os.path.basename(f)}")

# ==================================================================================
# PASS 1: SCAN ALL FILES
# Collect (machine_id, person_id, person_gender, week_of_sample) — minimal columns
# ==================================================================================
print("\n" + "=" * 80)
print("PASS 1: SCANNING INTERMEDIATE FILES")
print("=" * 80)

COLUMNS_TO_READ = ["machine_id", "week_of_sample"]

presence_chunks = []    # for machine_week_presence
week_to_files = defaultdict(list)  # for boundary week detection

for i, file in enumerate(intermediate_files, 1):
    fname = os.path.basename(file)
    print(f"\n  [{i}/{len(intermediate_files)}] {fname}")

    df = pd.read_parquet(file, columns=COLUMNS_TO_READ)
    print(f"    Rows loaded: {len(df):,}")

    # --- machine_week_presence ---
    presence = df[["machine_id", "week_of_sample"]].drop_duplicates()
    presence_chunks.append(presence)

    # --- boundary week tracking ---
    weeks_in_file = df["week_of_sample"].unique()
    for w in weeks_in_file:
        week_to_files[w].append(fname)

    print(f"    Unique (machine, week) pairs: {len(presence):,}")
    print(
        f"    Week range: {df['week_of_sample'].min()} to {df['week_of_sample'].max()}"
    )

# ==================================================================================
# BUILD machine_week_presence
# ==================================================================================
print("\n" + "=" * 80)
print("BUILDING machine_week_presence")
print("=" * 80)

machine_week_presence = (
    pd.concat(presence_chunks, ignore_index=True)
    .drop_duplicates()
    .sort_values(["machine_id", "week_of_sample"])
    .reset_index(drop=True)
)

print(f"  Total (machine_id, week_of_sample) pairs: {len(machine_week_presence):,}")
print(f"  Unique machine_ids:  {machine_week_presence['machine_id'].nunique():,}")
print(f"  Unique weeks:        {machine_week_presence['week_of_sample'].nunique():,}")
print(
    f"  Week range:          {machine_week_presence['week_of_sample'].min()} "
    f"to {machine_week_presence['week_of_sample'].max()}"
)

presence_path = os.path.join(output_dir, "machine_week_presence.parquet")
machine_week_presence.to_parquet(presence_path, index=False, engine="pyarrow")
print(f"\n  Saved to: {presence_path}")

# ==================================================================================
# BUILD boundary_weeks.csv
# ==================================================================================
print("\n" + "=" * 80)
print("BUILDING boundary_weeks.csv")
print("=" * 80)

boundary_weeks = sorted(
    week for week, files in week_to_files.items() if len(files) > 1
)
non_boundary_weeks = sorted(
    week for week, files in week_to_files.items() if len(files) == 1
)

print(f"  Total unique weeks:          {len(week_to_files)}")
print(f"  Boundary weeks (multi-file): {len(boundary_weeks)}")
print(f"  Non-boundary weeks:          {len(non_boundary_weeks)}")

if boundary_weeks:
    print("\n  Boundary week details:")
    for w in boundary_weeks:
        print(f"    Week {w:3d}: {', '.join(week_to_files[w])}")

boundary_df = pd.DataFrame(
    [
        {"week_of_sample": w, "files": ", ".join(week_to_files[w])}
        for w in boundary_weeks
    ]
)
boundary_path = os.path.join(output_dir, "boundary_weeks.csv")
boundary_df.to_csv(boundary_path, index=False)
print(f"\n  Saved to: {boundary_path}")

# ==================================================================================
# SUMMARY
# ==================================================================================
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Intermediate files scanned:  {len(intermediate_files)}")
print(f"Unique machines:             {machine_week_presence['machine_id'].nunique():,}")
print(f"Unique (machine, week) rows: {len(machine_week_presence):,}")
print(f"Boundary weeks identified:   {len(boundary_weeks)}")
print(f"\nOutputs:")
print(f"  {presence_path}")
print(f"  {boundary_path}")
print("=" * 80)
print("COMPLETE")
print("=" * 80)
