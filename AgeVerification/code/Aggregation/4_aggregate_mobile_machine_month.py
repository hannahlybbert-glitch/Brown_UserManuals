# Author: Emily Davis
# Created: 03/10/2026
# Purpose: Aggregate one month of mobile sessions to machine_id x week_of_sample, split by coarse category

"""
Mobile Machine-Level Monthly Aggregation (Script 4 of 5 — Mobile Pipeline)
Mirrors 4_aggregate_machine_month.py for the desktop pipeline.

Reads the mobile intermediate session file for one calendar month and aggregates to
machine_id × week_of_sample, computing total_duration. Outputs 9 separate parquet
files — one per coarse category (category stored in the filename, not as a column).

Run once per month (36 times total). Parallelizable on cluster.

Usage:   python 4_aggregate_mobile_machine_month.py YYYYMM
Example: python 4_aggregate_mobile_machine_month.py 202201

Input:
  data/Aggregation/mobile_intermediate/{month_id}/mobile_intermediate_sessions_YYYYMM.parquet

Output (9 files per month, 324 total):
  data/Aggregation/mobile_machine_panel/monthly/{coarse_category}/
      mobile_machine_month_YYYYMM_{coarse_category}.parquet
  Columns: machine_id, week_of_sample, total_duration

Note on boundary weeks:
  Sessions near month boundaries may produce partial week data in this file.
  Duplicate (machine_id, week_of_sample) rows from adjacent months are resolved
  in script 5 by summing total_duration — correct because duration is additive.
"""

import pandas as pd
import os
import sys
from glob import glob

project_root = os.getcwd()

# ----- COMMAND LINE ARGUMENTS ----- #
TEST_MODE = "--test" in sys.argv
args = [a for a in sys.argv[1:] if a != "--test"]

if len(args) != 1:
    print("Usage: python 4_aggregate_mobile_machine_month.py YYYYMM [--test]")
    print("Example: python 4_aggregate_mobile_machine_month.py 202201")
    sys.exit(1)

yyyymm = args[0]

print("=" * 80)
print(f"MOBILE MACHINE-LEVEL MONTHLY AGGREGATION: {yyyymm}" + (" [TEST MODE]" if TEST_MODE else ""))
print("=" * 80)

# ----- FILE PATHS ----- #
intermediate_dir = os.path.join(
    project_root, "data", "Aggregation",
    "mobile_intermediate_test" if TEST_MODE else "mobile_intermediate"
)
top_websites_file = os.path.join(project_root, "data", "Aggregation", "top5_xxx_websites.csv")
output_base = os.path.join(
    project_root, "data", "Aggregation",
    "mobile_machine_panel_test" if TEST_MODE else "mobile_machine_panel",
    "monthly"
)

matches = glob(
    os.path.join(intermediate_dir, "*", f"mobile_intermediate_sessions_{yyyymm}.parquet")
)
if len(matches) == 0:
    print(f"ERROR: No mobile intermediate file found for {yyyymm} in {intermediate_dir}")
    print("Please run script 2 first.")
    sys.exit(1)
if len(matches) > 1:
    print(f"WARNING: Multiple matches found for {yyyymm}; using first: {matches[0]}")

intermediate_file = matches[0]

# ----- LOAD CATEGORY LIST ----- #
print(f"\n[1/3] Loading coarse category list...")
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

# ----- LOAD SESSIONS ----- #
print(f"\n[2/3] Loading mobile sessions from {os.path.basename(intermediate_file)}...")
COLUMNS_TO_READ = ["machine_id", "week_of_sample", "coarse_category", "duration"]
sessions = pd.read_parquet(intermediate_file, columns=COLUMNS_TO_READ)

print(f"  Loaded {len(sessions):,} sessions")
print(f"  Week range: {sessions['week_of_sample'].min()} to {sessions['week_of_sample'].max()}")
print(f"  Unique machines: {sessions['machine_id'].nunique():,}")

observed_cats = sessions["coarse_category"].unique()
print(f"  Categories observed: {len(observed_cats)}")

# ----- AGGREGATE AND SAVE BY CATEGORY ----- #
print(f"\n[3/3] Aggregating and saving by coarse category...")

for cat in all_coarse_categories:
    cat_dir = os.path.join(output_base, cat)
    os.makedirs(cat_dir, exist_ok=True)
    output_file = os.path.join(cat_dir, f"mobile_machine_month_{yyyymm}_{cat}.parquet")

    cat_sessions = sessions[sessions["coarse_category"] == cat]

    if len(cat_sessions) == 0:
        empty = pd.DataFrame(columns=["machine_id", "week_of_sample", "total_duration"])
        empty.to_parquet(output_file, index=False, engine="pyarrow")
        print(f"  {cat:40s}: 0 sessions — saved empty file")
        continue

    agg = (
        cat_sessions
        .groupby(["machine_id", "week_of_sample"], as_index=False)["duration"]
        .sum()
        .rename(columns={"duration": "total_duration"})
    )

    agg.to_parquet(output_file, index=False, engine="pyarrow")
    print(
        f"  {cat:40s}: {len(cat_sessions):>10,} sessions → "
        f"{len(agg):>8,} machine-week rows"
    )

# ==================================================================================
# SUMMARY
# ==================================================================================
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Month processed: {yyyymm}")
print(f"Sessions read:   {len(sessions):,}")
print(f"Output files:    {len(all_coarse_categories)} (one per coarse category)")
print(f"Output location: {output_base}/{{category}}/mobile_machine_month_{yyyymm}_{{category}}.parquet")
print("=" * 80)
print("COMPLETE")
print("=" * 80)
