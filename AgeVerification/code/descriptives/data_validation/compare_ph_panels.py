# Author: Hannah Lybbert, assisted by Claude
# Created: 2026-05-21
# Purpose: Compare machine_aggregated_PORNHUB.COM.parquet from the original
#          combined pipeline vs the new top-25 pipeline.
#          Helps diagnose any differences in total_duration / baseline mean.
#
# Usage:
#   python3 code/descriptives/data_validation/compare_ph_panels.py

import os
import numpy as np
import pandas as pd

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

ORIG_PATH = os.path.join(
    project_root, "data", "Aggregation",
    "desktop_mobile_machine_panel",
    "machine_aggregated_PORNHUB.COM.parquet"
)
TOP25_PATH = os.path.join(
    project_root, "data", "Aggregation", "top25",
    "desktop_mobile_machine_panel",
    "machine_aggregated_PORNHUB.COM.parquet"
)

BASELINE_WEEKS = range(1, 53)   # 2022 weeks used in compute_p95_2022

# ============================================================================
# LOAD
# ============================================================================

print("=" * 70)
print("PORNHUB.COM PANEL COMPARISON — original vs top-25")
print("=" * 70)

print(f"\nLoading original: {ORIG_PATH}")
orig  = pd.read_parquet(ORIG_PATH)
print(f"Loading top-25:   {TOP25_PATH}")
top25 = pd.read_parquet(TOP25_PATH)

# ============================================================================
# BASIC SHAPE & COLUMNS
# ============================================================================

print("\n--- SHAPE & COLUMNS ---")
print(f"{'':20s}  {'Original':>15}  {'Top-25':>15}")
print(f"{'Rows':20s}  {len(orig):>15,}  {len(top25):>15,}")
print(f"{'Columns':20s}  {orig.shape[1]:>15}  {top25.shape[1]:>15}")
print(f"\nOriginal columns: {list(orig.columns)}")
print(f"Top-25 columns:   {list(top25.columns)}")

# ============================================================================
# COVERAGE
# ============================================================================

print("\n--- COVERAGE ---")
print(f"{'':30s}  {'Original':>12}  {'Top-25':>12}")
print(f"{'Unique machines':30s}  {orig['machine_id'].nunique():>12,}  {top25['machine_id'].nunique():>12,}")
print(f"{'Unique weeks':30s}  {orig['week_of_sample'].nunique():>12,}  {top25['week_of_sample'].nunique():>12,}")
print(f"{'Week range':30s}  {orig['week_of_sample'].min()}-{orig['week_of_sample'].max():>3}      {top25['week_of_sample'].min()}-{top25['week_of_sample'].max():>3}")

# Mobile column breakdown if present in both
if 'mobile' in orig.columns and 'mobile' in top25.columns:
    print(f"\n{'Mobile=0 rows':30s}  {(orig['mobile']==0).sum():>12,}  {(top25['mobile']==0).sum():>12,}")
    print(f"{'Mobile=1 rows':30s}  {(orig['mobile']==1).sum():>12,}  {(top25['mobile']==1).sum():>12,}")

# ============================================================================
# total_duration STATS (all weeks)
# ============================================================================

def dur_stats(s):
    return {
        'N':       len(s),
        'N_zero':  (s == 0).sum(),
        'N_null':  s.isna().sum(),
        'N_pos':   (s > 0).sum(),
        'mean':    s.mean(),
        'std':     s.std(),
        'p25':     s.quantile(0.25),
        'median':  s.median(),
        'p75':     s.quantile(0.75),
        'p95':     s.quantile(0.95),
        'p99':     s.quantile(0.99),
        'max':     s.max(),
    }

d_orig  = dur_stats(orig['total_duration'].fillna(0))
d_top25 = dur_stats(top25['total_duration'].fillna(0))

print("\n--- total_duration STATS (all weeks, NaN→0) ---")
print(f"{'Stat':12s}  {'Original':>15}  {'Top-25':>15}  {'Diff':>15}")
for k in d_orig:
    fmt = f"{d_orig[k]:>15,.1f}" if isinstance(d_orig[k], float) else f"{d_orig[k]:>15,}"
    fmt2 = f"{d_top25[k]:>15,.1f}" if isinstance(d_top25[k], float) else f"{d_top25[k]:>15,}"
    if isinstance(d_orig[k], float):
        diff = f"{d_top25[k] - d_orig[k]:>+15.1f}"
    else:
        diff = f"{d_top25[k] - d_orig[k]:>+15,}"
    print(f"  {k:12s}  {fmt}  {fmt2}  {diff}")

# ============================================================================
# total_duration STATS — 2022 BASELINE WEEKS ONLY (what compute_p95_2022 uses)
# ============================================================================

orig_bl  = orig[orig['week_of_sample'].isin(BASELINE_WEEKS)]['total_duration'].fillna(0)
top25_bl = top25[top25['week_of_sample'].isin(BASELINE_WEEKS)]['total_duration'].fillna(0)

d_orig_bl  = dur_stats(orig_bl)
d_top25_bl = dur_stats(top25_bl)

print("\n--- total_duration STATS — 2022 BASELINE WEEKS (weeks 1–52) ---")
print(f"  (These determine compute_p95_2022 — i.e. the win_min cap)")
print(f"{'Stat':12s}  {'Original':>15}  {'Top-25':>15}  {'Diff':>15}")
for k in d_orig_bl:
    fmt = f"{d_orig_bl[k]:>15,.1f}" if isinstance(d_orig_bl[k], float) else f"{d_orig_bl[k]:>15,}"
    fmt2 = f"{d_top25_bl[k]:>15,.1f}" if isinstance(d_top25_bl[k], float) else f"{d_top25_bl[k]:>15,}"
    if isinstance(d_orig_bl[k], float):
        diff = f"{d_top25_bl[k] - d_orig_bl[k]:>+15.1f}"
    else:
        diff = f"{d_top25_bl[k] - d_orig_bl[k]:>+15,}"
    print(f"  {k:12s}  {fmt}  {fmt2}  {diff}")

print(f"\n  => Original p95 (seconds):  {d_orig_bl['p95']:,.1f}  ({d_orig_bl['p95']/60:.2f} min)")
print(f"  => Top-25  p95 (seconds):  {d_top25_bl['p95']:,.1f}  ({d_top25_bl['p95']/60:.2f} min)")

# ============================================================================
# MACHINE OVERLAP
# ============================================================================

orig_machines  = set(orig['machine_id'].unique())
top25_machines = set(top25['machine_id'].unique())

only_orig  = orig_machines  - top25_machines
only_top25 = top25_machines - orig_machines
both       = orig_machines  & top25_machines

print("\n--- MACHINE OVERLAP ---")
print(f"  In both:        {len(both):>10,}")
print(f"  Only original:  {len(only_orig):>10,}")
print(f"  Only top-25:    {len(only_top25):>10,}")

# ============================================================================
# MATCHED-MACHINE total_duration COMPARISON
# (same machine × week, do durations agree?)
# ============================================================================

if len(both) > 0:
    common_cols = ['machine_id', 'week_of_sample', 'total_duration']
    orig_sub  = orig[orig['machine_id'].isin(both)][common_cols].rename(
        columns={'total_duration': 'dur_orig'})
    top25_sub = top25[top25['machine_id'].isin(both)][common_cols].rename(
        columns={'total_duration': 'dur_top25'})

    merged = orig_sub.merge(top25_sub, on=['machine_id', 'week_of_sample'], how='inner')
    merged['dur_orig']  = merged['dur_orig'].fillna(0)
    merged['dur_top25'] = merged['dur_top25'].fillna(0)
    merged['diff']      = merged['dur_top25'] - merged['dur_orig']

    exact_match = (merged['diff'] == 0).sum()
    total_rows  = len(merged)

    print("\n--- MATCHED machine×week DURATION COMPARISON ---")
    print(f"  Matched rows:       {total_rows:>10,}")
    print(f"  Exact match:        {exact_match:>10,}  ({100*exact_match/total_rows:.2f}%)")
    print(f"  Rows with diff:     {(merged['diff'] != 0).sum():>10,}")
    if (merged['diff'] != 0).any():
        diffs = merged[merged['diff'] != 0]['diff']
        print(f"  Diff mean:          {diffs.mean():>10.2f}s")
        print(f"  Diff std:           {diffs.std():>10.2f}s")
        print(f"  Diff min:           {diffs.min():>10.2f}s")
        print(f"  Diff max:           {diffs.max():>10.2f}s")

print("\n" + "=" * 70)
print("DONE")
print("=" * 70)
