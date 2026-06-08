#!/usr/bin/env python3
# Author: Hannah Lybbert
# Created: 04/23/2026
# Purpose: For ever-treated machines (analysis_sample == 1), report how many unique
#          states they come from and a machine count breakdown by state.
#          Includes diagnostics to catch machine_id issues in the demographics files.

'''
Sample definition
  Restricted to machines with analysis_sample == 1. State is pulled from the
  full_*_demos files via inner join; desktop and mobile are pooled and
  deduplicated so each machine appears once. Machines with no demographics
  match are excluded. Machines whose state is not in the treated-states list
  from statelaws_dates.csv are flagged and excluded from the output table.

Input files
  data/Aggregation/machine_activity/machine_week_activity.parquet           (machine universe + ever_treated)
  data/ProcessComscore/full_demographics/full_machine_person_demos.parquet  (desktop state)
  data/ProcessComscore/full_demographics/full_mobile_demos.parquet          (mobile state)
  raw/statelaws/phshutdown_dates.csv                                        (ground-truth treated state list)

Output files (in output/descriptives/summary_tables/)
  treated_states_summary.tex / .md

Usage: python code/descriptives/summary_tables/treated_states_summary.py
'''

import os
import pandas as pd
import numpy as np

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

DESKTOP_DEMOS = os.path.join(BASE, "data", "ProcessComscore", "full_demographics",
                             "full_machine_person_demos.parquet")
MOBILE_DEMOS  = os.path.join(BASE, "data", "ProcessComscore", "full_demographics",
                             "full_mobile_demos.parquet")
ACTIVITY_FILE = os.path.join(BASE, "data", "Aggregation", "machine_activity",
                             "machine_week_activity.parquet")
STATE_LAWS    = os.path.join(BASE, "raw", "statelaws", "phshutdown_dates.csv")
OUTPUT_DIR    = os.path.join(BASE, "output", "descriptives", "summary_tables")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ── Load treated-state ground truth from phshutdown_dates.csv ──────────────────
print("Loading treated states from phshutdown_dates.csv...")
laws = pd.read_csv(STATE_LAWS)
treated_states = set(laws.loc[laws["date_PH_shutdown"].notna(), "state"])
print(f"  Treated states ({len(treated_states)}): {sorted(treated_states)}")


# ── Load machine universe ──────────────────────────────────────────────────────
print("\nLoading machine universe from machine_week_activity.parquet...")
activity = pd.read_parquet(ACTIVITY_FILE, columns=["machine_id", "ever_treated", "analysis_sample"])
activity["machine_id"] = activity["machine_id"].astype(str)
machine_universe = (
    activity.drop_duplicates("machine_id")
    [["machine_id", "ever_treated", "analysis_sample"]]
    .copy()
)
machine_universe = machine_universe[machine_universe["analysis_sample"] == 1].drop(columns="analysis_sample")
print(f"  {len(machine_universe):,} machines with analysis_sample == 1")
print(f"  Ever-treated:  {(machine_universe['ever_treated'] == 1).sum():,}")
print(f"  Never-treated: {(machine_universe['ever_treated'] == 0).sum():,}")


# ── Load state info ────────────────────────────────────────────────────────────
print("\nLoading state info from demographics files...")
desktop_states = pd.read_parquet(DESKTOP_DEMOS, columns=["machine_id", "state"])
mobile_states  = pd.read_parquet(MOBILE_DEMOS,  columns=["machine_id", "state"])
desktop_states["machine_id"] = desktop_states["machine_id"].astype(str)
mobile_states["machine_id"]  = mobile_states["machine_id"].astype(str)


# ── Build combined state lookup and join onto machine universe ─────────────────
print("\n" + "=" * 60)
print("  BUILDING STATE LOOKUP")
print("=" * 60)

all_states = (
    pd.concat([desktop_states, mobile_states], ignore_index=True)
    .drop_duplicates("machine_id")
)
print(f"  {len(all_states):,} machines with state info (desktop + mobile combined)")

# Inner join: only machines already in the activity file can appear here.
# machine_week_activity.parquet was built with XX/ZZ/US machines excluded,
# so those machine_ids will not be present in machine_universe and cannot
# re-enter via this join.
machines = machine_universe.merge(all_states, on="machine_id", how="inner")
print(f"  {len(machines):,} analysis-sample machines matched to state info")

n_no_match = len(machine_universe) - len(machines)
if n_no_match:
    print(f"  NOTE: {n_no_match:,} analysis-sample machines had no demographics match "
          f"-- excluded")


# ── Diagnostic 3: ever_treated == 1 machines with unexpected states ────────────
print("\n" + "=" * 60)
print("  DIAGNOSTIC 3: ever_treated == 1 STATE AUDIT")
print("=" * 60)

ever_treated_all = machines[machines["ever_treated"] == 1].copy()
print(f"  Total machines with ever_treated == 1: {len(ever_treated_all):,}")

# Machines in a valid treated state
valid_mask   = ever_treated_all["state"].isin(treated_states)
invalid_mask = ~valid_mask

n_valid   = valid_mask.sum()
n_invalid = invalid_mask.sum()
print(f"  State is a treated state (expected):   {n_valid:,}")
print(f"  State is NOT a treated state (PROBLEM): {n_invalid:,}")

if n_invalid > 0:
    problem = ever_treated_all[invalid_mask].copy()
    problem_by_state = (
        problem.groupby("state", as_index=False)
        .size()
        .rename(columns={"size": "n_machines"})
        .sort_values("n_machines", ascending=False)
    )
    print(f"\n  Breakdown of problem ever_treated machines by state:")
    print(f"  {'State':<10} {'N Machines':>12}  Note")
    print(f"  {'-'*10} {'-'*12}  {'-'*30}")
    for _, row in problem_by_state.iterrows():
        print(f"  {row['state']:<10} {row['n_machines']:>12,}  non-treated state -- should never be ever_treated")
    print(f"\n  These machines are EXCLUDED from the output table below.")
    print(f"  Root cause should be investigated in 7_machine_week_activity.py.")


# ── Ever-treated state counts (valid treated states only) ──────────────────────
ever_treated = ever_treated_all[valid_mask].copy()

state_counts = (
    ever_treated.groupby("state", as_index=False)
    .size()
    .rename(columns={"size": "n_machines"})
    .sort_values("state")
)
n_states = ever_treated["state"].nunique()

# Flag any treated states from statelaws_dates.csv that are absent entirely
missing_treated = treated_states - set(ever_treated["state"])
if missing_treated:
    print(f"\n  NOTE: {len(missing_treated)} treated state(s) from statelaws_dates.csv have "
          f"zero ever_treated machines in the analysis sample:")
    print(f"    {sorted(missing_treated)}")

print("\n" + "=" * 60)
print("  EVER-TREATED MACHINES BY STATE (valid treated states only)")
print("=" * 60)
print(f"  {'State':<10} {'N Machines':>12}")
print(f"  {'-'*10} {'-'*12}")
for _, row in state_counts.iterrows():
    print(f"  {row['state']:<10} {row['n_machines']:>12,}")
print(f"  {'-'*10} {'-'*12}")
print(f"  {'Total':<10} {len(ever_treated):>12,}")
print(f"\n  Unique treated states with machines: {n_states}")


# ── Export ─────────────────────────────────────────────────────────────────────
def export_tex(path):
    lines = [
        r"\begin{table}[h!]",
        r"\centering",
        r"\caption{Ever-Treated Machines by State (Analysis Sample)}",
        r"\label{tab:treated_states}",
        r"\begin{tabular}{lr}",
        r"\toprule",
        r"State & N Machines \\",
        r"\midrule",
    ]
    for _, row in state_counts.iterrows():
        lines.append(f"{row['state']} & {row['n_machines']:,} \\\\")
    lines += [
        r"\midrule",
        f"Total & {len(ever_treated):,} \\\\",
        r"\midrule",
        f"\\multicolumn{{2}}{{l}}{{Unique treated states: {n_states}}} \\\\",
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  Saved: {path}")


def export_md(path):
    lines = [
        "## Ever-Treated Machines by State (Analysis Sample)\n",
        f"*Machines with `analysis_sample == 1`, `ever_treated == 1`, and a valid "
        f"treated state. Unique treated states: **{n_states}**.*\n",
        "| State | N Machines |",
        "| --- | ---: |",
    ]
    for _, row in state_counts.iterrows():
        lines.append(f"| {row['state']} | {row['n_machines']:,} |")
    lines.append(f"| **Total** | **{len(ever_treated):,}** |")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  Saved: {path}")


print("\n" + "=" * 60)
print("  SAVING OUTPUT FILES")
print("=" * 60)
export_tex(os.path.join(OUTPUT_DIR, "treated_states_summary.tex"))
export_md( os.path.join(OUTPUT_DIR, "treated_states_summary.md"))

print("\n" + "=" * 60)
print("  COMPLETE")
print("=" * 60)
