# Author: Hannah Lybbert
# Created: 03/30/2026
# Purpose: Stack desktop and mobile machine panels into combined panel files

"""
Append Desktop and Mobile Machine Panels (Script 6)
For each category found in machine_panel/ and/or mobile_machine_panel/, stacks the
desktop and mobile parquet files into a single combined file.

Adds:
  mobile            — 1 if row is from the mobile panel, 0 if from the desktop panel

Overlap check: logs a warning (with machine_ids listed) if any machine_id appears in
both the desktop and mobile panels for a given category. There should be none.

Dynamic category detection: categories are inferred from files present in both source
directories, so new categories are picked up automatically without changing this script.

Usage: python 6_append_desktop_mobile_panels.py

Input:
  data/Aggregation/machine_panel/machine_aggregated_{category}.parquet         (script 5)
  data/Aggregation/mobile_machine_panel/machine_aggregated_{category}.parquet  (script 5 mobile)

Output:
  data/Aggregation/desktop_mobile_machine_panel/machine_aggregated_{category}.parquet
  Columns: machine_id, week_of_sample, total_duration, mobile
"""

import pandas as pd
import os
from glob import glob

# For cluster: comment out the os.chdir line
# os.chdir(r"C:\Users\hlybbert\OneDrive - The University of Chicago\Documents\AgeVerification")

project_root = os.getcwd()

print("=" * 80)
print("APPEND DESKTOP AND MOBILE MACHINE PANELS")
print("=" * 80)

# ----- FILE PATHS ----- #
desktop_dir = os.path.join(project_root, "data", "Aggregation", "machine_panel")
mobile_dir  = os.path.join(project_root, "data", "Aggregation", "mobile_machine_panel")
output_dir  = os.path.join(project_root, "data", "Aggregation", "desktop_mobile_machine_panel")

os.makedirs(output_dir, exist_ok=True)

# ----- DISCOVER CATEGORIES ----- #
# Union of categories found in either directory
def get_categories(directory):
    files = glob(os.path.join(directory, "machine_aggregated_*.parquet"))
    return {os.path.basename(f).replace("machine_aggregated_", "").replace(".parquet", "") for f in files}

desktop_cats = get_categories(desktop_dir)
mobile_cats  = get_categories(mobile_dir)
all_cats     = sorted(desktop_cats | mobile_cats)

print(f"\n[SETUP] Categories discovered:")
print(f"  Desktop only:  {sorted(desktop_cats - mobile_cats) or 'none'}")
print(f"  Mobile only:   {sorted(mobile_cats - desktop_cats) or 'none'}")
print(f"  In both:       {sorted(desktop_cats & mobile_cats)}")
print(f"  Total:         {len(all_cats)}")

# ==================================================================================
# PROCESS ONE CATEGORY AT A TIME
# ==================================================================================
for cat_idx, cat in enumerate(all_cats, 1):
    print("\n" + "=" * 80)
    print(f"[{cat_idx}/{len(all_cats)}] CATEGORY: {cat}")
    print("=" * 80)

    desktop_file = os.path.join(desktop_dir, f"machine_aggregated_{cat}.parquet")
    mobile_file  = os.path.join(mobile_dir,  f"machine_aggregated_{cat}.parquet")
    output_file  = os.path.join(output_dir,  f"machine_aggregated_{cat}.parquet")

    chunks = []

    if os.path.exists(desktop_file):
        df_desktop = pd.read_parquet(desktop_file)
        df_desktop["mobile"] = 0
        chunks.append(df_desktop)
        print(f"  Desktop rows: {len(df_desktop):,}")
    else:
        print(f"  Desktop file not found — skipping desktop for this category")

    if os.path.exists(mobile_file):
        df_mobile = pd.read_parquet(mobile_file)
        df_mobile["mobile"] = 1
        chunks.append(df_mobile)
        print(f"  Mobile rows:  {len(df_mobile):,}")
    else:
        print(f"  Mobile file not found — skipping mobile for this category")

    if len(chunks) == 0:
        print(f"  ERROR: No files found for category '{cat}' — skipping")
        continue

    combined = pd.concat(chunks, ignore_index=True)

    # ----- OVERLAP CHECK ----- #
    # There should be no machine_ids appearing in both the desktop and mobile panels.
    # Log a warning (with the offending IDs) if any are found.
    if len(chunks) == 2:
        desktop_machines = set(df_desktop["machine_id"].unique())
        mobile_machines  = set(df_mobile["machine_id"].unique())
        overlap_machines = desktop_machines & mobile_machines
        print(f"  Machines in desktop panel:  {len(desktop_machines):,}")
        print(f"  Machines in mobile panel:   {len(mobile_machines):,}")
        if overlap_machines:
            print(f"  WARNING: {len(overlap_machines):,} machine_id(s) appear in BOTH panels:")
            for mid in sorted(overlap_machines):
                print(f"    {mid}")
        else:
            print(f"  Overlap check passed — no machine_ids appear in both panels")

    # Enforce column order and sort
    combined = combined[["machine_id", "week_of_sample", "total_duration", "mobile"]]
    combined = combined.sort_values(["mobile", "machine_id", "week_of_sample"]).reset_index(drop=True)

    combined.to_parquet(output_file, index=False, engine="pyarrow")

    print(f"  Combined rows: {len(combined):,}")
    print(f"  Saved: {output_file}")

# ==================================================================================
# FINAL SUMMARY
# ==================================================================================
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Categories processed: {len(all_cats)}")
print(f"\nOutput files:")
for cat in all_cats:
    out = os.path.join(output_dir, f"machine_aggregated_{cat}.parquet")
    print(f"  {out}")
print("=" * 80)
print("COMPLETE")
print("=" * 80)
