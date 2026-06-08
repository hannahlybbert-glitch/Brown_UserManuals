# Author: Emily Davis
# Created: 03/10/2026
# Purpose: Build mobile machine roster files for mobile machine-level panel assembly

"""
Build Mobile Machine Roster (Script 3 of 5 — Mobile Pipeline)
Mirrors 3_build_machine_roster.py for the desktop pipeline.

Scans all 36 mobile intermediate session files and outputs:

  1. machine_week_presence.parquet  — one row per (machine_id, week_of_sample) observed;
                                      ground truth for the NULL vs. zero distinction in script 5
  2. boundary_weeks.csv            — weeks that span two calendar months (appear in 2+ files)

Run once before scripts 4 and 5. No arguments required.

Usage: python 3_build_mobile_machine_roster.py
"""

import pandas as pd
import os
import sys
from glob import glob
from collections import defaultdict

project_root = os.getcwd()

TEST_MODE = "--test" in sys.argv

print("=" * 80)
print("BUILD MOBILE MACHINE ROSTER" + (" [TEST MODE]" if TEST_MODE else ""))
print("=" * 80)

# ----- FILE PATHS ----- #
intermediate_dir = os.path.join(
    project_root, "data", "Aggregation",
    "mobile_intermediate_test" if TEST_MODE else "mobile_intermediate"
)
output_dir = os.path.join(
    project_root, "data", "Aggregation",
    "mobile_machine_panel_test" if TEST_MODE else "mobile_machine_panel"
)
os.makedirs(output_dir, exist_ok=True)

# ----- FIND ALL INTERMEDIATE FILES ----- #
print(f"\n[SETUP] Finding mobile intermediate session files...")
intermediate_files = sorted(
    glob(os.path.join(intermediate_dir, "*", "mobile_intermediate_sessions_*.parquet"))
)

if len(intermediate_files) == 0:
    print(f"ERROR: No mobile intermediate files found in {intermediate_dir}")
    print("Please run script 2 first.")
    exit(1)

print(f"  Found {len(intermediate_files)} intermediate files:")
for f in intermediate_files:
    print(f"    - {os.path.basename(f)}")

# ==================================================================================
# PASS 1: SCAN ALL FILES
# ==================================================================================
print("\n" + "=" * 80)
print("PASS 1: SCANNING MOBILE INTERMEDIATE FILES")
print("=" * 80)

COLUMNS_TO_READ = ["machine_id", "week_of_sample"]

presence_chunks = []
week_to_files = defaultdict(list)

for i, file in enumerate(intermediate_files, 1):
    fname = os.path.basename(file)
    print(f"\n  [{i}/{len(intermediate_files)}] {fname}")

    df = pd.read_parquet(file, columns=COLUMNS_TO_READ)
    print(f"    Rows loaded: {len(df):,}")

    presence = df[["machine_id", "week_of_sample"]].drop_duplicates()
    presence_chunks.append(presence)

    weeks_in_file = df["week_of_sample"].unique()
    for w in weeks_in_file:
        week_to_files[w].append(fname)

    print(f"    Unique (machine, week) pairs: {len(presence):,}")
    print(f"    Week range: {df['week_of_sample'].min()} to {df['week_of_sample'].max()}")

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
print(f"  Week range:          {machine_week_presence['week_of_sample'].min()} "
      f"to {machine_week_presence['week_of_sample'].max()}")

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
