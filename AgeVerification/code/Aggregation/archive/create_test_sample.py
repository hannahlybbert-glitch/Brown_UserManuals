# Author: Hannah Lybbert
# Created: 02/23/2026
# Purpose: Create a small two-month test dataset for local pipeline validation

"""
Create Test Sample
Builds a small two-month test dataset from the Jan 2022 intermediate file so that
the full pipeline (scripts 3–5) can be validated quickly without cluster access.

Outputs to data/Aggregation/intermediate_test/ (never touches the real data).

The synthetic second month is created by shifting week_of_sample by 4, so that
the last week of "202201" and first week of "202202" overlap — this exercises
the boundary-week handling in scripts 3 and 5.

Usage: python create_test_sample.py
       python create_test_sample.py --machines 500   (default: 1000)

Then run the pipeline in test mode:
  python code/Aggregation/3_build_machine_roster.py --test
  python code/Aggregation/4_aggregate_machine_month.py 202201 --test
  python code/Aggregation/4_aggregate_machine_month.py 202202 --test
  python code/Aggregation/5_assemble_machine_panel.py --test
"""

import pandas as pd
import numpy as np
import os
import sys

os.chdir(r"C:\Users\hlybbert\OneDrive - The University of Chicago\Documents\AgeVerification")
project_root = os.getcwd()

# ----- CONFIG ----- #
# Number of machines to sample. Adjust downward for faster tests.
N_MACHINES = 1000
if "--machines" in sys.argv:
    idx = sys.argv.index("--machines")
    N_MACHINES = int(sys.argv[idx + 1])

WEEK_SHIFT = 4   # weeks to shift for synthetic month 2 (creates a boundary week at the overlap)
OVERLAP_FRAC = 0.9  # fraction of month-1 machines also present in month 2

print("=" * 80)
print("CREATE TEST SAMPLE")
print("=" * 80)
print(f"  Machines to sample: {N_MACHINES:,}")
print(f"  Week shift for month 2: {WEEK_SHIFT}")
print(f"  Month-1/2 machine overlap: {int(OVERLAP_FRAC * 100)}%")

# ----- PATHS ----- #
source_file = os.path.join(
    project_root, "data", "Aggregation", "intermediate", "265",
    "intermediate_sessions_202201.parquet"
)
out_dir_1 = os.path.join(project_root, "data", "Aggregation", "intermediate_test", "265")
out_dir_2 = os.path.join(project_root, "data", "Aggregation", "intermediate_test", "266")
os.makedirs(out_dir_1, exist_ok=True)
os.makedirs(out_dir_2, exist_ok=True)

# ----- LOAD SOURCE ----- #
print(f"\n[1/3] Loading source file: {os.path.basename(source_file)}")
df = pd.read_parquet(source_file)
print(f"  Sessions: {len(df):,}")
print(f"  Unique machines: {df['machine_id'].nunique():,}")
print(f"  Week range: {df['week_of_sample'].min()} to {df['week_of_sample'].max()}")

# ----- BUILD MONTH 1 (202201) ----- #
print(f"\n[2/3] Building test month 202201 ({N_MACHINES:,} sampled machines)...")
all_machines = df["machine_id"].unique()
rng = np.random.default_rng(42)
sampled_machines = rng.choice(
    all_machines, size=min(N_MACHINES, len(all_machines)), replace=False
)

sample_202201 = df[df["machine_id"].isin(sampled_machines)].copy()
print(f"  Sessions: {len(sample_202201):,}")
print(f"  Machines: {sample_202201['machine_id'].nunique():,}")
print(f"  Week range: {sample_202201['week_of_sample'].min()} to {sample_202201['week_of_sample'].max()}")

out_1 = os.path.join(out_dir_1, "intermediate_sessions_202201.parquet")
sample_202201.to_parquet(out_1, index=False, engine="pyarrow")
print(f"  Saved: {out_1}")

# ----- BUILD MONTH 2 (202202, synthetic) ----- #
print(f"\n[3/3] Building synthetic test month 202202 (week_of_sample + {WEEK_SHIFT})...")

# 90% of month-1 machines reappear (simulates panel continuity with some attrition)
n_overlap = int(OVERLAP_FRAC * len(sampled_machines))
machines_month2 = rng.choice(sampled_machines, size=n_overlap, replace=False)

sample_202202 = df[df["machine_id"].isin(machines_month2)].copy()
sample_202202["week_of_sample"] = sample_202202["week_of_sample"] + WEEK_SHIFT
sample_202202["week_start_date"] = (
    pd.to_datetime(sample_202202["week_start_date"]) + pd.Timedelta(weeks=WEEK_SHIFT)
)

print(f"  Sessions: {len(sample_202202):,}")
print(f"  Machines: {sample_202202['machine_id'].nunique():,}")
print(f"  Week range: {sample_202202['week_of_sample'].min()} to {sample_202202['week_of_sample'].max()}")

out_2 = os.path.join(out_dir_2, "intermediate_sessions_202202.parquet")
sample_202202.to_parquet(out_2, index=False, engine="pyarrow")
print(f"  Saved: {out_2}")

# ----- REPORT BOUNDARY WEEKS ----- #
weeks_1 = set(sample_202201["week_of_sample"].unique())
weeks_2 = set(sample_202202["week_of_sample"].unique())
boundary = sorted(weeks_1 & weeks_2)
print(f"\n  Boundary weeks (appear in both months): {boundary}")
print(f"  → Script 5 should sum these correctly when assembling the panel.")

# ==================================================================================
# SUMMARY
# ==================================================================================
print("\n" + "=" * 80)
print("COMPLETE — test data written to data/Aggregation/intermediate_test/")
print("=" * 80)
print("\nNext steps — run the pipeline in test mode:")
print("  python code/Aggregation/3_build_machine_roster.py --test")
print("  python code/Aggregation/4_aggregate_machine_month.py 202201 --test")
print("  python code/Aggregation/4_aggregate_machine_month.py 202202 --test")
print("  python code/Aggregation/5_assemble_machine_panel.py --test")
print("\nOutputs will be written to data/Aggregation/machine_panel_test/")
print("  (real data in machine_panel/ is untouched)")
print("=" * 80)
