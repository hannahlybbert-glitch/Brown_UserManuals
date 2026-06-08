# Author: Emily Davis
# Created: 03/10/2026
# Purpose: Assemble final mobile machine-level panel from monthly aggregated files

"""
Assemble Mobile Machine Panel (Script 5 of 5 — Mobile Pipeline)
Mirrors 5_assemble_machine_panel.py for the desktop pipeline.

Combines the 324 monthly category files produced by script 4 into 9 final panel files —
one per coarse category. Each output file covers all mobile machines × all 157 sample weeks.

Run once after all 36 invocations of script 4 have completed. No arguments required.

Usage: python 5_assemble_mobile_machine_panel.py

Input:
  data/Aggregation/mobile_machine_panel/machine_week_presence.parquet   (from script 3)
  data/ProcessComscore/mobile_characteristics.csv                        (from create_mobile_characteristics.py)
  data/Aggregation/mobile_machine_panel/monthly/{category}/
      mobile_machine_month_YYYYMM_{category}.parquet                     (from script 4, 324 files)
  data/Aggregation/top5_xxx_websites.csv                                 (from desktop script 1)

Output (9 files):
  data/Aggregation/mobile_machine_panel/machine_aggregated_{category}.parquet
  Columns: machine_id, week_of_sample, total_duration

NULL vs. zero convention:
  NULL (NaN)  — machine was NOT in the Comscore panel that week (no data exists)
  0           — machine WAS in the panel that week but had zero usage in this category

Boundary week handling:
  Weeks that span two calendar months appear in two monthly files with partial duration.
  Concatenating all 36 files and summing on duplicate (machine_id, week_of_sample)
  pairs correctly reconstructs the full-week total (duration is additive).

Note on demographics:
  Unlike the desktop pipeline, mobile_characteristics.csv contains one row per machine
  with no have_demos flag — every machine in the file has demographics by construction.
  All machines in the file are included in the panel grid.
"""

import pandas as pd
import numpy as np
import os
import sys
from glob import glob

project_root = os.getcwd()

TEST_MODE = "--test" in sys.argv

print("=" * 80)
print("ASSEMBLE MOBILE MACHINE PANEL" + (" [TEST MODE]" if TEST_MODE else ""))
print("=" * 80)

# ----- FILE PATHS ----- #
panel_dir = os.path.join(
    project_root, "data", "Aggregation",
    "mobile_machine_panel_test" if TEST_MODE else "mobile_machine_panel"
)
monthly_dir = os.path.join(panel_dir, "monthly")
top_websites_file = os.path.join(project_root, "data", "Aggregation", "top5_xxx_websites.csv")

presence_file = os.path.join(panel_dir, "machine_week_presence.parquet")
mobile_chars_file = os.path.join(project_root, "data", "ProcessComscore", "mobile_characteristics.csv")

# ----- LOAD ROSTER FILES ----- #
print(f"\n[SETUP] Loading roster files...")

machine_week_presence = pd.read_parquet(presence_file)
mobile_characteristics = pd.read_csv(mobile_chars_file, dtype={'machine_id': str})

# All machines in mobile_characteristics.csv have demographics — no have_demos filter needed
all_machine_ids = mobile_characteristics["machine_id"].values
all_weeks = sorted(machine_week_presence["week_of_sample"].unique())
n_machines = len(all_machine_ids)
n_weeks = len(all_weeks)

print(f"  Unique machines:  {n_machines:,}  (all have demographics)")
print(f"  Sample weeks:     {n_weeks}  (week {min(all_weeks)} to {max(all_weeks)})")
print(f"  Full grid size:   {n_machines * n_weeks:,} rows per category")


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
        glob(os.path.join(monthly_dir, cat, f"mobile_machine_month_*_{cat}.parquet"))
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
        monthly_agg = pd.DataFrame(
            columns=["machine_id", "week_of_sample", "total_duration"]
        )
    else:
        monthly_raw = pd.concat(chunks, ignore_index=True)
        print(f"    Total rows before boundary-week resolution: {len(monthly_raw):,}")

        # --- Step 2: Resolve boundary weeks by summing duplicates ---
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

    panel = full_grid.merge(monthly_agg, on=["machine_id", "week_of_sample"], how="left")

    # --- Step 4: Apply NULL vs. zero rule ---
    print(f"\n  [4/4] Applying NULL vs. zero rule via machine_week_presence...")
    presence_flag = machine_week_presence[["machine_id", "week_of_sample"]].copy()
    presence_flag["_in_panel"] = True
    panel = panel.merge(presence_flag, on=["machine_id", "week_of_sample"], how="left")
    panel["_in_panel"] = panel["_in_panel"].fillna(False).astype(bool)

    panel.loc[panel["total_duration"].isna() & panel["_in_panel"], "total_duration"] = 0.0
    panel = panel.drop(columns=["_in_panel"])

    n_null = panel["total_duration"].isna().sum()
    n_zero = (panel["total_duration"] == 0).sum()
    n_positive = (panel["total_duration"] > 0).sum()
    print(f"    total_duration breakdown:")
    print(f"      NULL (not in panel):      {n_null:>12,}")
    print(f"      Zero (in panel, no use):  {n_zero:>12,}")
    print(f"      Positive (has usage):     {n_positive:>12,}")

    panel = panel[["machine_id", "week_of_sample", "total_duration"]]
    panel = panel.sort_values(["machine_id", "week_of_sample"]).reset_index(drop=True)

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
