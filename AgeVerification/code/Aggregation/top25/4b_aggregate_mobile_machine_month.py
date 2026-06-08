# Author: Hannah Lybbert, assisted by Claude
# Created: 2026-05-21
# Purpose: Aggregate one month of top-25 mobile sessions to machine_id x week_of_sample
#          by coarse category. Mirrors 4b_aggregate_machine_month.py for mobile.
#
# Usage: python3 code/Aggregation/top25/4b_aggregate_mobile_machine_month.py YYYYMM
#
# Input:
#   data/Aggregation/top25/mobile_intermediate/{month_id}/mobile_intermediate_sessions_{YYYYMM}.parquet
#   output/ProcessComscore/data_structure_validation/top25_adult_sites.csv
#
# Output (26 files per month, 936 total):
#   data/Aggregation/top25/mobile_machine_panel/monthly/{category}/
#       mobile_machine_month_{YYYYMM}_{category}.parquet
#   Columns: machine_id, week_of_sample, total_duration

import pandas as pd
import os
import sys
from glob import glob

project_root = os.getcwd()

if len(sys.argv) != 2:
    print("Usage: python3 code/Aggregation/top25/4b_aggregate_mobile_machine_month.py YYYYMM")
    sys.exit(1)

yyyymm = sys.argv[1]

print("=" * 80)
print(f"TOP-25 MACHINE-LEVEL MONTHLY AGGREGATION (MOBILE): {yyyymm}")
print("=" * 80)

# ----- FILE PATHS ----- #
intermediate_dir = os.path.join(
    project_root, "data", "Aggregation", "top25", "mobile_intermediate"
)
top25_file = os.path.join(
    project_root, "output", "ProcessComscore", "data_structure_validation",
    "top25_adult_sites.csv"
)
output_base = os.path.join(
    project_root, "data", "Aggregation", "top25", "mobile_machine_panel", "monthly"
)

matches = glob(
    os.path.join(intermediate_dir, "*", f"mobile_intermediate_sessions_{yyyymm}.parquet")
)
if len(matches) == 0:
    print(f"ERROR: No mobile intermediate file found for {yyyymm} in {intermediate_dir}")
    print("Please run 2b_create_mobile_intermediate_sessions.py first.")
    sys.exit(1)
if len(matches) > 1:
    print(f"WARNING: Multiple matches found; using first: {matches[0]}")

intermediate_file = matches[0]

# ----- LOAD CATEGORY LIST ----- #
print(f"\n[1/3] Loading coarse category list...")
top25 = pd.read_csv(top25_file)
all_coarse_categories = top25['top_web_name'].tolist() + ['other_adult']
print(f"  Categories ({len(all_coarse_categories)} total):")
for cat in all_coarse_categories:
    print(f"    - {cat}")

# ----- LOAD SESSIONS ----- #
print(f"\n[2/3] Loading mobile sessions from {os.path.basename(intermediate_file)}...")
sessions = pd.read_parquet(
    intermediate_file,
    columns=["machine_id", "week_of_sample", "coarse_category", "duration"]
)
print(f"  Loaded {len(sessions):,} sessions")
print(f"  Week range: {sessions['week_of_sample'].min()} to {sessions['week_of_sample'].max()}")
print(f"  Unique machines: {sessions['machine_id'].nunique():,}")

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
        print(f"  {cat:35s}: 0 sessions — saved empty file")
        continue

    agg = (
        cat_sessions
        .groupby(["machine_id", "week_of_sample"], as_index=False)["duration"]
        .sum()
        .rename(columns={"duration": "total_duration"})
    )
    agg.to_parquet(output_file, index=False, engine="pyarrow")
    print(
        f"  {cat:35s}: {len(cat_sessions):>10,} sessions → "
        f"{len(agg):>8,} machine-week rows"
    )

print("\n" + "=" * 80)
print(f"COMPLETE — {yyyymm}")
print(f"  Output: {output_base}/{{category}}/mobile_machine_month_{yyyymm}_{{category}}.parquet")
print("=" * 80)
