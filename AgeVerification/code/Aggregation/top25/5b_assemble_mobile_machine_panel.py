# Author: Hannah Lybbert, assisted by Claude
# Created: 2026-05-21
# Purpose: Assemble final mobile machine-level panel for top-25 categories.
#          Mirrors 5_assemble_mobile_machine_panel.py.
#
# Reuses the existing mobile machine_week_presence.parquet and mobile_characteristics.csv
# from the original aggregation pipeline.
#
# Usage: python3 code/Aggregation/top25/5b_assemble_mobile_machine_panel.py
#
# Input:
#   data/Aggregation/top25/mobile_machine_panel/monthly/{category}/
#       mobile_machine_month_{YYYYMM}_{category}.parquet       (from 4b mobile, 936 files)
#   data/Aggregation/mobile_machine_panel/machine_week_presence.parquet  [existing]
#   data/ProcessComscore/mobile_characteristics.csv                       [existing]
#   output/ProcessComscore/data_structure_validation/top25_adult_sites.csv
#
# Output (26 files):
#   data/Aggregation/top25/mobile_machine_panel/machine_aggregated_{category}.parquet
#   Columns: machine_id, week_of_sample, total_duration

import pandas as pd
import os
import sys
from glob import glob

project_root = os.getcwd()

print("=" * 80)
print("ASSEMBLE TOP-25 MACHINE PANEL (MOBILE)")
print("=" * 80)

# ----- FILE PATHS ----- #
panel_dir   = os.path.join(project_root, "data", "Aggregation", "top25", "mobile_machine_panel")
monthly_dir = os.path.join(panel_dir, "monthly")
top25_file  = os.path.join(
    project_root, "output", "ProcessComscore", "data_structure_validation",
    "top25_adult_sites.csv"
)
# Reuse existing mobile presence and demographics
presence_file    = os.path.join(
    project_root, "data", "Aggregation", "mobile_machine_panel",
    "machine_week_presence.parquet"
)
mobile_chars_file = os.path.join(
    project_root, "data", "ProcessComscore", "mobile_characteristics.csv"
)

# ----- LOAD ROSTER FILES ----- #
print(f"\n[SETUP] Loading roster files...")
machine_week_presence  = pd.read_parquet(presence_file)
mobile_characteristics = pd.read_csv(mobile_chars_file, dtype={'machine_id': str})

# All machines in mobile_characteristics have demographics — no have_demos filter
all_machine_ids = mobile_characteristics["machine_id"].values
all_weeks       = sorted(machine_week_presence["week_of_sample"].unique())
n_machines      = len(all_machine_ids)
n_weeks         = len(all_weeks)

print(f"  Unique machines:  {n_machines:,}  (all have demographics)")
print(f"  Sample weeks:     {n_weeks}  (week {min(all_weeks)} to {max(all_weeks)})")
print(f"  Full grid size:   {n_machines * n_weeks:,} rows per category")

# ----- LOAD CATEGORY LIST ----- #
print(f"\n[SETUP] Loading coarse category list...")
top25 = pd.read_csv(top25_file)
all_coarse_categories = top25['top_web_name'].tolist() + ['other_adult']
print(f"  Categories ({len(all_coarse_categories)} total):")
for cat in all_coarse_categories:
    print(f"    - {cat}")

os.makedirs(panel_dir, exist_ok=True)

# ==================================================================================
# ASSEMBLE ONE CATEGORY AT A TIME
# ==================================================================================
for cat_idx, cat in enumerate(all_coarse_categories, 1):
    print("\n" + "=" * 80)
    print(f"[{cat_idx}/{len(all_coarse_categories)}] CATEGORY: {cat}")
    print("=" * 80)

    output_file   = os.path.join(panel_dir, f"machine_aggregated_{cat}.parquet")
    monthly_files = sorted(
        glob(os.path.join(monthly_dir, cat, f"mobile_machine_month_*_{cat}.parquet"))
    )
    print(f"\n  [1/4] Loading {len(monthly_files)} monthly files...")

    if len(monthly_files) == 0:
        print(f"  ERROR: No monthly files found for '{cat}'")
        print(f"         Expected: {os.path.join(monthly_dir, cat)}")
        print("         Please run 4b mobile for all 36 months first.")
        continue

    chunks = [pd.read_parquet(f) for f in monthly_files if len(pd.read_parquet(f)) > 0]

    if len(chunks) == 0:
        print("  All monthly files are empty.")
        monthly_agg = pd.DataFrame(columns=["machine_id", "week_of_sample", "total_duration"])
    else:
        monthly_raw = pd.concat(chunks, ignore_index=True)
        print(f"    Rows before boundary-week resolution: {len(monthly_raw):,}")

        print(f"\n  [2/4] Resolving boundary weeks...")
        monthly_agg = (
            monthly_raw
            .groupby(["machine_id", "week_of_sample"], as_index=False)["total_duration"]
            .sum()
        )
        print(f"    Rows after resolution: {len(monthly_agg):,}  "
              f"({len(monthly_raw)-len(monthly_agg):,} duplicate rows merged)")

    # --- Build full grid ---
    print(f"\n  [3/4] Building full grid ({n_machines:,} machines × {n_weeks} weeks)...")
    full_grid = pd.MultiIndex.from_product(
        [all_machine_ids, all_weeks], names=["machine_id", "week_of_sample"]
    ).to_frame(index=False)
    panel = full_grid.merge(monthly_agg, on=["machine_id", "week_of_sample"], how="left")

    # --- NULL vs. zero rule (merge approach, consistent with original mobile 5) ---
    print(f"\n  [4/4] Applying NULL vs. zero rule...")
    presence_flag = machine_week_presence[["machine_id", "week_of_sample"]].copy()
    presence_flag["_in_panel"] = True
    panel = panel.merge(presence_flag, on=["machine_id", "week_of_sample"], how="left")
    panel["_in_panel"] = panel["_in_panel"].fillna(False).astype(bool)
    panel.loc[panel["total_duration"].isna() & panel["_in_panel"], "total_duration"] = 0.0
    panel = panel.drop(columns=["_in_panel"])

    n_null     = panel["total_duration"].isna().sum()
    n_zero     = (panel["total_duration"] == 0).sum()
    n_positive = (panel["total_duration"] > 0).sum()
    print(f"    NULL (not in panel):     {n_null:>12,}")
    print(f"    Zero (in panel, no use): {n_zero:>12,}")
    print(f"    Positive (has usage):    {n_positive:>12,}")

    panel = (
        panel[["machine_id", "week_of_sample", "total_duration"]]
        .sort_values(["machine_id", "week_of_sample"])
        .reset_index(drop=True)
    )
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
    print(f"  {os.path.join(panel_dir, f'machine_aggregated_{cat}.parquet')}")
print("=" * 80)
print("COMPLETE")
print("=" * 80)
