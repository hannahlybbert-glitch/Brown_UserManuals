# Author: Hannah Lybbert
# Created: 02/17/2026
# Purpose: Troubleshoot zero-value rows in final_aggregated.csv
#
# SUSPECTED BUG:
#   The complete-grid merge in 3_aggregate_all_months.py creates rows for every
#   (state, week, category) combination. For categories with no sessions in a given
#   state-week, the left merge leaves all_machine_count = NaN, which gets filled with 0.
#   But all_machine_count should be the same nonzero value for all 7 categories in a
#   state-week (it reflects ALL machines active in that state that week, not just those
#   visiting that specific category).
#
#   Two distinct failure modes to distinguish:
#     A) Entire state-week has no data at all  → zeros may be expected (state not sampled)
#     B) State-week has data for SOME categories but zero all_machine_count for others
#        → definitely a bug (all_machine_count should propagate across all categories)
#
# Usage: Run from project root
#   python code/Aggregation/diagnose_final_aggregated.py

import sys
import pandas as pd
import numpy as np
import os

# Force UTF-8 output so Unicode characters don't crash on Windows cp1252 consoles
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

pd.set_option('display.max_columns', 20)
pd.set_option('display.width', 120)
pd.set_option('display.float_format', '{:,.2f}'.format)

print("=" * 80)
print("DIAGNOSING FINAL AGGREGATED CSV")
print("=" * 80)

# Local testing only - comment out when running from terminal
os.chdir(r"C:\Users\hlybbert\OneDrive - The University of Chicago\Documents\AgeVerification")

# ----- LOAD DATA ----- #
csv_path = os.path.join("data", "Aggregation", "aggregated_file", "final_aggregated.csv")
print(f"\nLoading {csv_path}...")
df = pd.read_csv(csv_path)
print(f"  Loaded {len(df):,} rows, {len(df.columns)} columns")
print(f"  Columns: {list(df.columns)}")

# ==================================================================================
# SECTION 1: OVERALL SHAPE CHECK
# ==================================================================================
print("\n" + "=" * 80)
print("SECTION 1: OVERALL SHAPE")
print("=" * 80)

n_states = df['state'].nunique()
n_weeks  = df['week_of_sample'].nunique()
n_cats   = df['coarse_category'].nunique()

print(f"\n  States:     {n_states}  (expected 50)")
print(f"  Weeks:      {n_weeks}  (expected 156)")
print(f"  Categories: {n_cats}  (expected 7)")
print(f"  Total rows: {len(df):,}  (expected {n_states * n_weeks * n_cats:,})")

print(f"\n  Week range: {df['week_of_sample'].min()} – {df['week_of_sample'].max()}")
print(f"  Date range: {df['week_start_date'].min()} – {df['week_start_date'].max()}")
print(f"\n  Unique states:     {sorted(df['state'].unique())}")
print(f"  Unique categories: {sorted(df['coarse_category'].unique())}")

# ==================================================================================
# SECTION 2: IDENTIFY ZERO / MISSING ROWS
# ==================================================================================
print("\n" + "=" * 80)
print("SECTION 2: ZERO / MISSING ROW COUNTS")
print("=" * 80)

# Rows where all counts are zero
all_zero_mask = (
    (df['all_machine_count'] == 0) &
    (df['all_person_count']  == 0) &
    (df['site_machine_count'] == 0) &
    (df['site_person_count']  == 0) &
    (df['total_duration_seconds'] == 0)
)
all_zero = df[all_zero_mask]

# Rows with NaN log fields
nan_log_mask = df['log_hrs_per_machine'].isna() | df['log_hrs_per_person'].isna()
nan_log = df[nan_log_mask]

# Rows where all_machine_count == 0 but at least one site count > 0  (internal inconsistency)
inconsistent_mask = (df['all_machine_count'] == 0) & (
    (df['site_machine_count'] > 0) | (df['site_person_count'] > 0) | (df['total_duration_seconds'] > 0)
)

print(f"\n  Rows where ALL counts = 0:          {len(all_zero):,}")
print(f"  Rows with NaN log fields:            {len(nan_log):,}")
print(f"  Inconsistent rows (site>0, all=0):   {inconsistent_mask.sum():,}")

# ==================================================================================
# SECTION 3: KEY DIAGNOSTIC — TYPE A vs TYPE B ZEROS
# ==================================================================================
print("\n" + "=" * 80)
print("SECTION 3: TYPE A vs TYPE B — ENTIRE STATE-WEEK ZERO vs PARTIAL ZERO")
print("=" * 80)
print("""
  Type A: The entire state-week has no data (all 7 categories have all_machine_count=0).
          May be expected if Comscore had no panel members in that state/week.

  Type B: Some categories in the state-week have non-zero all_machine_count but
          others show 0. This is a bug — all_machine_count should be the same for
          all 7 categories in a given state-week.
""")

# For each state-week, what is the MAX all_machine_count across all categories?
state_week_max_machines = df.groupby(['state', 'week_of_sample'])['all_machine_count'].max().reset_index()
state_week_max_machines.columns = ['state', 'week_of_sample', 'max_all_machine_count']

# Merge onto zero rows to classify them
zero_classified = all_zero.merge(state_week_max_machines, on=['state', 'week_of_sample'], how='left')

type_a_mask = zero_classified['max_all_machine_count'] == 0   # entire state-week is empty
type_b_mask = zero_classified['max_all_machine_count'] > 0    # state-week has data elsewhere → BUG

type_a = zero_classified[type_a_mask]
type_b = zero_classified[type_b_mask]

print(f"  Type A (entire state-week empty):   {len(type_a):,} rows")
print(f"  Type B (BUG — all_machine_count=0 despite state-week having data): {len(type_b):,} rows")

# ==================================================================================
# SECTION 4: TYPE A DETAIL — EMPTY STATE-WEEKS
# ==================================================================================
if len(type_a) > 0:
    print("\n" + "=" * 80)
    print("SECTION 4: TYPE A — EMPTY STATE-WEEKS (potential data gaps)")
    print("=" * 80)

    # These are state-weeks where the max across all categories is still 0
    empty_state_weeks = type_a.groupby(['state', 'week_of_sample']).size()
    empty_state_weeks = empty_state_weeks[empty_state_weeks == n_cats]  # all 7 categories are zero

    # Also find partial state-weeks in Type A (shouldn't happen but check)
    partial_type_a = type_a.groupby(['state', 'week_of_sample']).size()
    partial_type_a = partial_type_a[partial_type_a < n_cats]

    n_empty_sw = len(empty_state_weeks)
    print(f"\n  Fully empty state-weeks (all 7 categories zero): {n_empty_sw:,}")
    print(f"  Partial Type A (shouldn't exist):                 {len(partial_type_a):,}")

    if n_empty_sw > 0:
        print(f"\n  Breakdown by state:")
        by_state = empty_state_weeks.reset_index(level=0).groupby('state').size()
        for state, count in by_state.sort_values(ascending=False).items():
            print(f"    {state}: {count} empty weeks")

        print(f"\n  Distribution of empty weeks over time:")
        by_week = empty_state_weeks.reset_index(level=1).groupby('week_of_sample').size()
        # Show the 20 worst weeks (most states empty)
        worst_weeks = by_week.nlargest(20)
        for week, count in worst_weeks.items():
            week_date = df.loc[df['week_of_sample'] == week, 'week_start_date'].iloc[0]
            print(f"    Week {week:>4} ({week_date}): {count} states with no data")

# ==================================================================================
# SECTION 5: TYPE B DETAIL — THE BUG
# ==================================================================================
print("\n" + "=" * 80)
print("SECTION 5: TYPE B — BUG DETAILS (all_machine_count=0 despite active state-week)")
print("=" * 80)

if len(type_b) > 0:
    print(f"\n  {len(type_b):,} rows have all_machine_count=0 in a state-week that has non-zero data elsewhere.")
    print("  ROOT CAUSE: After the complete-grid LEFT merge in 3_aggregate_all_months.py,")
    print("  categories with no sessions get all_machine_count=NaN -> filled with 0.")
    print("  all_machine_count should be the same for all 7 categories in a state-week.\n")

    print("  Breakdown by category (which categories are affected):")
    by_cat = type_b.groupby('coarse_category').size().sort_values(ascending=False)
    for cat, count in by_cat.items():
        pct = count / len(df[df['coarse_category'] == cat]) * 100
        print(f"    {cat:<30} {count:>6,} rows  ({pct:5.1f}% of that category's rows)")

    print(f"\n  Sample Type B rows (showing state-week context):")
    # Show a few Type B rows with the all_machine_count from other categories in that state-week
    sample_sw = type_b[['state', 'week_of_sample', 'coarse_category']].head(10)
    for _, row in sample_sw.iterrows():
        state, week, cat = row['state'], row['week_of_sample'], row['coarse_category']
        other_cats = df[(df['state'] == state) & (df['week_of_sample'] == week) & (df['all_machine_count'] > 0)]
        if len(other_cats) > 0:
            correct_machines = other_cats['all_machine_count'].iloc[0]
            week_date = other_cats['week_start_date'].iloc[0]
            print(f"    {state}, week {week} ({week_date}), {cat}: "
                  f"all_machine_count=0 but should be {correct_machines:.0f}")

    # How many unique state-weeks are affected?
    affected_sw = type_b[['state', 'week_of_sample']].drop_duplicates()
    print(f"\n  Unique state-weeks with at least one Type B row: {len(affected_sw):,}")

else:
    print("\n  No Type B rows found. all_machine_count propagation appears correct.")

# ==================================================================================
# SECTION 6: ALL_MACHINE_COUNT CONSISTENCY WITHIN STATE-WEEKS
# ==================================================================================
print("\n" + "=" * 80)
print("SECTION 6: ALL_MACHINE_COUNT CONSISTENCY WITHIN STATE-WEEKS")
print("=" * 80)
print("  (For state-weeks with any data, all 7 categories should have identical all_machine_count)\n")

# For state-weeks with non-zero max, check if all categories share the same all_machine_count
state_week_nonzero = df.groupby(['state', 'week_of_sample']).filter(
    lambda g: g['all_machine_count'].max() > 0
)

machine_count_variance = state_week_nonzero.groupby(['state', 'week_of_sample'])['all_machine_count'].nunique()
inconsistent_sw = machine_count_variance[machine_count_variance > 1]

print(f"  State-weeks where all_machine_count varies across categories: {len(inconsistent_sw):,}")
if len(inconsistent_sw) > 0:
    print(f"  (Should be 0 if all_machine_count is correctly propagated)")
    print(f"\n  Sample inconsistent state-weeks:")
    for (state, week), n_unique in inconsistent_sw.head(5).items():
        subset = df[(df['state'] == state) & (df['week_of_sample'] == week)][
            ['coarse_category', 'all_machine_count', 'site_machine_count', 'total_duration_seconds']
        ]
        print(f"\n    {state}, week {week}:")
        print(subset.to_string(index=False))

# ==================================================================================
# SECTION 7: POTENTIAL FIX PREVIEW
# ==================================================================================
print("\n" + "=" * 80)
print("SECTION 7: POTENTIAL FIX — PROPAGATE all_machine_count WITHIN STATE-WEEKS")
print("=" * 80)
print("""
  The fix should go into 3_aggregate_all_months.py, after the complete-grid merge
  and fillna(0) block, and before calculating log metrics.

  After the LEFT merge with the complete grid, rows for categories with no sessions
  have all_machine_count=0. We can fix this by propagating the correct value from
  other categories within the same (state, week_of_sample).

  Proposed fix (add after line ~319 in 3_aggregate_all_months.py):

      # Fix: propagate all_machine_count and all_person_count within state-weeks.
      # After the complete-grid merge, some category rows have all_machine_count=0
      # because that category had no sessions — but all_machine_count reflects the
      # entire state-week population, not just visitors to that category.
      state_week_totals_fixed = (
          aggregated[aggregated['all_machine_count'] > 0]
          .groupby(['state', 'week_of_sample'])[['all_machine_count', 'all_person_count']]
          .first()
          .reset_index()
      )
      aggregated = aggregated.drop(columns=['all_machine_count', 'all_person_count'])
      aggregated = aggregated.merge(state_week_totals_fixed, on=['state', 'week_of_sample'], how='left')
      aggregated['all_machine_count'] = aggregated['all_machine_count'].fillna(0)
      aggregated['all_person_count']  = aggregated['all_person_count'].fillna(0)

  After this fix:
    - Type B rows (bug): all_machine_count will be correctly filled in
    - Type A rows (entire empty state-weeks): will remain 0 (correct behavior)
    - log_hrs_per_machine/person for rows where site had no visits but state-week
      had data: still NaN (correct -- total_duration_seconds=0, so ln undefined)
""")

# ==================================================================================
# SECTION 8: INTERMEDIATE DATA CHECK (if available)
# ==================================================================================
print("\n" + "=" * 80)
print("SECTION 8: INTERMEDIATE DATA SPOT CHECK")
print("=" * 80)

intermediate_dir = os.path.join("data", "Aggregation", "intermediate")
parquet_files = []
for root, dirs, files in os.walk(intermediate_dir):
    for f in files:
        if f.endswith('.parquet'):
            parquet_files.append(os.path.join(root, f))

print(f"\n  Found {len(parquet_files)} intermediate parquet file(s):")
for pf in sorted(parquet_files):
    print(f"    {os.path.relpath(pf)}")

if len(parquet_files) > 0 and len(type_b) > 0:
    # Spot-check: pick a Type B state-week from the first covered month
    # and verify the sessions exist in the intermediate data
    sample_b = type_b.iloc[0]
    state_b, week_b, cat_b = sample_b['state'], sample_b['week_of_sample'], sample_b['coarse_category']
    print(f"\n  Spot-checking Type B example: {state_b}, week {week_b}, {cat_b}")

    found = False
    for pf in sorted(parquet_files):
        try:
            tmp = pd.read_parquet(pf, columns=['state', 'week_of_sample', 'coarse_category', 'machine_id'])
            in_file = tmp[
                (tmp['state'] == state_b) &
                (tmp['week_of_sample'] == week_b)
            ]
            if len(in_file) > 0:
                found = True
                print(f"    {os.path.basename(pf)}: {len(in_file):,} sessions in this state-week")
                cat_sessions = in_file[in_file['coarse_category'] == cat_b]
                print(f"      Sessions with category '{cat_b}': {len(cat_sessions):,}")
                print(f"      All_machine count for this state-week: {in_file['machine_id'].nunique():,}")
            del tmp
        except Exception as e:
            print(f"    Error reading {os.path.basename(pf)}: {e}")

    if not found:
        print(f"    State-week not found in available intermediate files.")
        print(f"    (May be in a month not yet processed.)")

# ==================================================================================
# SUMMARY
# ==================================================================================
print("\n" + "=" * 80)
print("DIAGNOSIS SUMMARY")
print("=" * 80)
print(f"""
  Total rows in final_aggregated.csv:  {len(df):,}
  Rows with all counts = 0:            {len(all_zero):,}
    Type A (entire state-week empty):  {len(type_a):,}   ← possibly expected
    Type B (bug — should have data):   {len(type_b):,}   ← root cause identified

  State-weeks with any Type B row:     {len(type_b[['state','week_of_sample']].drop_duplicates()) if len(type_b)>0 else 0:,}
  State-weeks with inconsistent
    all_machine_count across cats:     {len(inconsistent_sw):,}

  → See SECTION 7 above for the proposed fix to 3_aggregate_all_months.py
""")
