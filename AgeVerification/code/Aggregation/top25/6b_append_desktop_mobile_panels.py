# Author: Hannah Lybbert, assisted by Claude
# Created: 2026-05-21
# Purpose: Stack top-25 desktop and mobile machine panels into combined files.
#          Mirrors 6_append_desktop_mobile_panels.py for the top-25 pipeline.
#
# Dynamically discovers categories from files present in either source directory,
# so no code changes are needed if the category list changes.
#
# Usage: python3 code/Aggregation/top25/6b_append_desktop_mobile_panels.py
#
# Input:
#   data/Aggregation/top25/machine_panel/machine_aggregated_{category}.parquet
#   data/Aggregation/top25/mobile_machine_panel/machine_aggregated_{category}.parquet
#
# Output:
#   data/Aggregation/top25/desktop_mobile_machine_panel/machine_aggregated_{category}.parquet
#   Columns: machine_id, week_of_sample, total_duration, mobile

import pandas as pd
import os
from glob import glob

project_root = os.getcwd()

print("=" * 80)
print("APPEND TOP-25 DESKTOP AND MOBILE MACHINE PANELS")
print("=" * 80)

# ----- FILE PATHS ----- #
desktop_dir = os.path.join(project_root, "data", "Aggregation", "top25", "machine_panel")
mobile_dir  = os.path.join(project_root, "data", "Aggregation", "top25", "mobile_machine_panel")
output_dir  = os.path.join(project_root, "data", "Aggregation", "top25", "desktop_mobile_machine_panel")
os.makedirs(output_dir, exist_ok=True)

# ----- DISCOVER CATEGORIES ----- #
def get_categories(directory):
    files = glob(os.path.join(directory, "machine_aggregated_*.parquet"))
    return {
        os.path.basename(f).replace("machine_aggregated_", "").replace(".parquet", "")
        for f in files
    }

desktop_cats = get_categories(desktop_dir)
mobile_cats  = get_categories(mobile_dir)
all_cats     = sorted(desktop_cats | mobile_cats)

print(f"\n[SETUP] Categories discovered:")
print(f"  Desktop only: {sorted(desktop_cats - mobile_cats) or 'none'}")
print(f"  Mobile only:  {sorted(mobile_cats - desktop_cats) or 'none'}")
print(f"  In both:      {sorted(desktop_cats & mobile_cats)}")
print(f"  Total:        {len(all_cats)}")

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
        df_desktop         = pd.read_parquet(desktop_file)
        df_desktop["mobile"] = 0
        chunks.append(df_desktop)
        print(f"  Desktop rows: {len(df_desktop):,}")
    else:
        print(f"  Desktop file not found — skipping desktop for this category")

    if os.path.exists(mobile_file):
        df_mobile          = pd.read_parquet(mobile_file)
        df_mobile["mobile"] = 1
        chunks.append(df_mobile)
        print(f"  Mobile rows:  {len(df_mobile):,}")
    else:
        print(f"  Mobile file not found — skipping mobile for this category")

    if len(chunks) == 0:
        print(f"  ERROR: No files found for '{cat}' — skipping")
        continue

    combined = pd.concat(chunks, ignore_index=True)

    # Overlap check — no machine_id should appear in both panels
    if len(chunks) == 2:
        desktop_machines = set(df_desktop["machine_id"].unique())
        mobile_machines  = set(df_mobile["machine_id"].unique())
        overlap          = desktop_machines & mobile_machines
        print(f"  Machines in desktop: {len(desktop_machines):,}")
        print(f"  Machines in mobile:  {len(mobile_machines):,}")
        if overlap:
            print(f"  WARNING: {len(overlap):,} machine_id(s) appear in BOTH panels:")
            for mid in sorted(overlap):
                print(f"    {mid}")
        else:
            print(f"  Overlap check passed — no machine_ids in both panels")

    combined = (
        combined[["machine_id", "week_of_sample", "total_duration", "mobile"]]
        .sort_values(["mobile", "machine_id", "week_of_sample"])
        .reset_index(drop=True)
    )
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
    print(f"  {os.path.join(output_dir, f'machine_aggregated_{cat}.parquet')}")
print("=" * 80)
print("COMPLETE")
print("=" * 80)
