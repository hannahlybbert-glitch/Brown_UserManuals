# Author: Hannah Lybbert
# Created: 02/23/2026
# Purpose: Assemble final machine-level panel from monthly aggregated files

"""
Assemble Machine Panel (Script 5 of 5)
Combines the 324 monthly category files produced by script 4 into 9 final panel files —
one per coarse category. Each output file covers all machines × all 157 sample weeks.

Run once after all 36 invocations of script 4 have completed. No arguments required.

Usage: python 5_assemble_machine_panel.py

Input:
  data/Aggregation/machine_panel/machine_week_presence.parquet         (from script 3)
  data/ProcessComscore/full_demographics/machine_demographics.parquet  (from create_full_demographics.py)
  data/Aggregation/machine_panel/monthly/{category}/
      machine_month_YYYYMM_{category}.parquet                          (from script 4, 324 files)
  data/Aggregation/top5_xxx_websites.csv                               (from script 1)

Output (9 files):
  data/Aggregation/machine_panel/machine_aggregated_{category}.parquet
  Columns: machine_id, week_of_sample, total_duration

NULL vs. zero convention:
  NULL (NaN)  — machine was NOT in the Comscore panel that week (no data exists)
  0           — machine WAS in the panel that week but had zero usage in this category

Boundary week handling:
  Weeks that span two calendar months appear in two monthly files with partial duration.
  Concatenating all 36 files and summing on duplicate (machine_id, week_of_sample)
  pairs correctly reconstructs the full-week total (duration is additive).
"""

import pandas as pd
import numpy as np
import os
import sys
from glob import glob

# For cluster: comment out the os.chdir line
# os.chdir(r"C:\Users\hlybbert\OneDrive - The University of Chicago\Documents\AgeVerification")

# Get the project root directory
project_root = os.getcwd()

# --test flag: use machine_panel_test/ instead of real output directory
TEST_MODE = "--test" in sys.argv

print("=" * 80)
print("ASSEMBLE MACHINE PANEL" + (" [TEST MODE]" if TEST_MODE else ""))
print("=" * 80)

# ----- FILE PATHS ----- #
panel_dir = os.path.join(
    project_root, "data", "Aggregation",
    "machine_panel_test" if TEST_MODE else "machine_panel"
)
monthly_dir = os.path.join(panel_dir, "monthly")
top_websites_file = os.path.join(project_root, "data", "Aggregation", "top5_xxx_websites.csv")

presence_file = os.path.join(panel_dir, "machine_week_presence.parquet")
demo_file = os.path.join(project_root, "data", "ProcessComscore", "full_demographics", "full_machine_person_demos.parquet")

# ----- LOAD ROSTER FILES ----- #
print(f"\n[SETUP] Loading roster files...")

machine_week_presence = pd.read_parquet(presence_file)
machine_demographics = pd.read_parquet(demo_file)

# Keep only machines with demographic data; drops machines with have_demos==0
# to reduce grid size and avoid loading data for machines we can't use.
machine_demographics = machine_demographics[machine_demographics["have_demos"] == 1]

all_machine_ids = machine_demographics["machine_id"].values
all_weeks = sorted(machine_week_presence["week_of_sample"].unique())
n_machines = len(all_machine_ids)
n_weeks = len(all_weeks)

print(f"  Unique machines:  {n_machines:,}  (have_demos==1 only)")
print(f"  Sample weeks:     {n_weeks}  (week {min(all_weeks)} to {max(all_weeks)})")
print(f"  Full grid size:   {n_machines * n_weeks:,} rows per category")

# Build a presence lookup as a MultiIndex for vectorized membership testing
presence_index = pd.MultiIndex.from_arrays(
    [machine_week_presence["machine_id"], machine_week_presence["week_of_sample"]],
    names=["machine_id", "week_of_sample"],
)

# ----- LOAD CATEGORY LIST ----- #
print(f"\n[SETUP] Loading coarse category list...")
top_websites = pd.read_csv(top_websites_file)
all_coarse_categories = top_websites["website_name"].tolist() + [
    "other_XXX_sites",
    "Netflix Inc.",
    "Reddit",
    "Twitter",
    "ONLYFANS.COM",
    "New York Times Digital",
    "Facebook",
    "INSTRUCTURE.COM",
    "Wikimedia Foundation Sites",
    "eBay",
    "Amazon Sites",
    "DUCKDUCKGO.COM",
    "Enthusiast Gaming",
    "Bytedance Inc.",
    "VPNclean",
    "allVPN",
    "all_other_sites",
]
print(f"  Categories ({len(all_coarse_categories)} total):")
for cat in all_coarse_categories:
    print(f"    - {cat}")

# ==================================================================================
# ASSEMBLE ONE CATEGORY AT A TIME
# ==================================================================================
for cat_idx, cat in enumerate(all_coarse_categories, 1):
    print("\n" + "=" * 80)
    print(f"[{cat_idx}/{len(all_coarse_categories)}] CATEGORY: {cat}")
    print("=" * 80)

    output_file = os.path.join(panel_dir, f"machine_aggregated_{cat}.parquet")

    # --- Step 1: Load and concatenate all 36 monthly files for this category ---
    monthly_files = sorted(
        glob(os.path.join(monthly_dir, cat, f"machine_month_*_{cat}.parquet"))
    )
    print(f"\n  [1/4] Loading {len(monthly_files)} monthly files...")

    if len(monthly_files) == 0:
        print(f"  ERROR: No monthly files found for category '{cat}'")
        print(f"         Expected location: {os.path.join(monthly_dir, cat)}")
        print("         Please run script 4 for all 36 months first.")
        continue

    chunks = []
    for f in monthly_files:
        df = pd.read_parquet(f)
        if len(df) > 0:
            chunks.append(df)

    if len(chunks) == 0:
        print("  All monthly files are empty — no sessions in this category.")
        # Still produce a full grid with NULLs / zeros
        monthly_agg = pd.DataFrame(
            columns=["machine_id", "week_of_sample", "total_duration"]
        )
    else:
        monthly_raw = pd.concat(chunks, ignore_index=True)
        print(f"    Total rows before boundary-week resolution: {len(monthly_raw):,}")

        # --- Step 2: Resolve boundary weeks by summing duplicates ---
        # Weeks spanning two calendar months appear in two monthly files with partial
        # totals. Groupby-sum correctly reconstructs the full-week duration.
        print(f"\n  [2/4] Resolving boundary weeks (summing duplicate machine-week rows)...")
        monthly_agg = (
            monthly_raw
            .groupby(["machine_id", "week_of_sample"], as_index=False)["total_duration"]
            .sum()
        )
        n_dropped = len(monthly_raw) - len(monthly_agg)
        print(f"    Rows after resolution: {len(monthly_agg):,}  ({n_dropped:,} duplicate rows merged)")

    # --- Step 3: Build full grid (all machines × all weeks) ---
    print(f"\n  [3/4] Building full grid ({n_machines:,} machines × {n_weeks} weeks)...")
    full_grid = pd.MultiIndex.from_product(
        [all_machine_ids, all_weeks], names=["machine_id", "week_of_sample"]
    ).to_frame(index=False)
    print(f"    Grid rows: {len(full_grid):,}")

    # Left-join actual usage onto the grid
    panel = full_grid.merge(monthly_agg, on=["machine_id", "week_of_sample"], how="left")

    # --- Step 4: Apply NULL vs. zero rule ---
    print(f"\n  [4/4] Applying NULL vs. zero rule via machine_week_presence...")
    # Rows with NaN total_duration are either:
    #   (a) machine was in panel but had no usage → set to 0
    #   (b) machine was not in panel that week    → leave as NaN (NULL)

    # Flag which (machine, week) combos are in the panel (vectorized)
    panel_index = pd.MultiIndex.from_arrays(
        [panel["machine_id"], panel["week_of_sample"]]
    )
    panel["_in_panel"] = panel_index.isin(presence_index)

    # Zero-fill for in-panel, no-usage rows; leave NULL for out-of-panel rows
    panel.loc[panel["total_duration"].isna() & panel["_in_panel"], "total_duration"] = 0.0
    panel = panel.drop(columns=["_in_panel"])

    n_null = panel["total_duration"].isna().sum()
    n_zero = (panel["total_duration"] == 0).sum()
    n_positive = (panel["total_duration"] > 0).sum()
    print(f"    total_duration breakdown:")
    print(f"      NULL (not in panel):      {n_null:>12,}")
    print(f"      Zero (in panel, no use):  {n_zero:>12,}")
    print(f"      Positive (has usage):     {n_positive:>12,}")

    # Enforce column order
    panel = panel[["machine_id", "week_of_sample", "total_duration"]]
    panel = panel.sort_values(["machine_id", "week_of_sample"]).reset_index(drop=True)

    # --- Save ---
    panel.to_parquet(output_file, index=False, engine="pyarrow")
    print(f"\n  Saved: {output_file}")
    print(f"  Shape: {panel.shape[0]:,} rows × {panel.shape[1]} columns")

# ==================================================================================
# FINAL SUMMARY
# ==================================================================================
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Categories assembled: {len(all_coarse_categories)}")
print(f"Machines:             {n_machines:,}")
print(f"Sample weeks:         {n_weeks}")
print(f"Rows per file:        {n_machines * n_weeks:,}")
print(f"\nOutput files:")
for cat in all_coarse_categories:
    out = os.path.join(panel_dir, f"machine_aggregated_{cat}.parquet")
    print(f"  {out}")
print("=" * 80)
print("COMPLETE")
print("=" * 80)
